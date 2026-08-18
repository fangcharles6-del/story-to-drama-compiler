# Creative Sample Qualification Decision Finalization v2.2

## Purpose and present-stage restriction

This runbook defines the trusted local file boundary for an independent Pack-level Human Review
v2 Qualification Decision. It has exactly three commands:

```text
inspect-decision-ready
finalize-decision
verify-decision
```

This development PR is **synthetic-only**. Do not substitute the current real private Frozen
Pack, Evidence, Reviews, PairCheck, Request, Qualifier reference, instruction or Decision into any
example or test. A real private invocation requires a later explicit approval naming every exact
absolute path. Approval to inspect does not approve finalization, and approval to finalize does
not approve a rights manifest or any execution action.

`finalize-decision` is the only command that creates a Decision and performs the scoped
qualification recorded by SDC-ADR-021. `inspect-decision-ready` must not call the pure Decision
builder. `verify-decision` only reconstructs the historical closure of an existing Decision and
writes nothing.

No command creates a rights manifest or grants Runtime permission. Keep this state throughout:

```text
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
rights_manifest_created=false
eligible_for_real_generation=false
```

## Command interface

The launcher is:

```text
python -m sdc.real_asset_qualification_decision_finalizer_v22 <subcommand> <options>
```

Every path is supplied separately as an absolute, ordinary, repository-external local path. The
program does not scan a directory, expand a wildcard, select a newest file, consult a mutable
alias, infer a sibling name or fill a missing option.

All three commands use this explicit common closure:

| Input role / option | Count | Required binding |
|---|---:|---|
| Frozen Pack root / `--pack-root` | 1 | Exact selected frozen directory; never a discovered Pack. |
| Frozen Pack manifest / `--pack-manifest` | 1 | Path must equal `<pack-root>/asset-pack.json`; strict canonical manifest and stable Pack ID. |
| Frozen media / repeated `--media-path` | 14 | Exactly fourteen occurrences in manifest ordinal order; each exact path, size and SHA-256 must match its descriptor. |
| Rights Evidence / `--evidence` | 1 | Strict Pack-level `CreativeSampleRealAssetRightsEvidenceBundleV2`. |
| Reviewer A / `--reviewer-a` | 1 | Strict finalized Pack review with role `REVIEWER_A`. |
| Reviewer B / `--reviewer-b` | 1 | Strict finalized Pack review with role `REVIEWER_B`. |
| PairCheck / `--pair-check` | 1 | Strict exact A/B PairCheck, status `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`, empty issues. |
| Retained Evidence record / `--evidence-retained-record` | 1 | Whole-file SHA-256 equals Evidence `evidence_record_sha256`. |
| Evidence Preparer reference / `--evidence-preparer-ref` | 1 | Whole-file SHA-256 equals Request `evidence_preparer_ref_sha256`. |
| Reviewer A retained reference / `--reviewer-a-retained-record` | 1 | Whole-file SHA-256 equals Reviewer A `reviewer_ref_sha256`. |
| Reviewer B retained reference / `--reviewer-b-retained-record` | 1 | Whole-file SHA-256 equals Reviewer B `reviewer_ref_sha256`. |
| Qualification Request / `--request` | 1 | Strict canonical `CreativeSampleRealAssetQualificationRequestV2`, exactly reconstructible from the preceding sources. |
| Qualifier reference / `--qualifier-ref` | 1 | Independent retained Qualifier identity/reference record; whole-file SHA-256 equals the instruction binding. |
| Qualifier instruction / `--qualifier-decision-record` | 1 | Strict canonical `CreativeSampleRealAssetQualificationDecisionInstructionV22`; its whole-file SHA-256 becomes the Decision `qualifier_record_sha256`. |

Operation-specific options are:

| Command | Additional required options | Forbidden implication |
|---|---|---|
| `inspect-decision-ready` | `--observed-at <YYYY-MM-DDTHH:MM:SSZ>` | No output path; no Decision builder call; no qualification performed. |
| `finalize-decision` | `--observed-at <YYYY-MM-DDTHH:MM:SSZ>` and `--output <absolute-new-decision.json>` | Output must be absent and is created once; no manifest. |
| `verify-decision` | `--decision-file <absolute-existing-decision.json>` | No observed time, no clock, no write or repair. |

There are deliberately no CLI options for `decision_at`, `decision`, `qualification_basis` or
`qualification_issue_codes`. Those human conclusions exist only in the complete canonical
Qualifier instruction. Do not add them through a wrapper, environment variable, interactive
prompt or generated default.

The common option skeleton is shown only to document the reviewed interface. Angle-bracketed
values are placeholders, not literal paths, and a wildcard must never replace them:

```text
--pack-root <absolute-pack-root>
--pack-manifest <absolute-pack-root>/asset-pack.json
--media-path <absolute-media-ordinal-00>
...repeat --media-path exactly once for each ordinal through 13...
--evidence <absolute-evidence-contract.json>
--reviewer-a <absolute-reviewer-a-contract.json>
--reviewer-b <absolute-reviewer-b-contract.json>
--pair-check <absolute-pair-check-contract.json>
--evidence-retained-record <absolute-evidence-record>
--evidence-preparer-ref <absolute-evidence-preparer-reference>
--reviewer-a-retained-record <absolute-reviewer-a-reference>
--reviewer-b-retained-record <absolute-reviewer-b-reference>
--request <absolute-qualification-request.json>
--qualifier-ref <absolute-qualifier-reference>
--qualifier-decision-record <absolute-canonical-instruction.json>
```

Append `--observed-at <YYYY-MM-DDTHH:MM:SSZ>` for `inspect-decision-ready`; append
`--observed-at <YYYY-MM-DDTHH:MM:SSZ> --output <absolute-new-decision.json>` for
`finalize-decision`; or append
`--decision-file <absolute-existing-decision.json>` for `verify-decision`. Never exchange or omit
these operation-specific options.

## Qualifier instruction checklist

`CreativeSampleRealAssetQualificationDecisionInstructionV22` is a versioned v2.2 canonical JSON
contract and the retained Qualifier decision record. Its committed Schema is a format contract,
not a conclusion template that the tool is allowed to fill. A human Qualifier must explicitly
provide every non-constant conclusion under the separately approved process.

The instruction binds the following fields and invariants:

| Field | Rule |
|---|---|
| `schema_version` | Exact v2.2 contract value `2.2.0`. |
| `document_type` | Fixed `sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2`. |
| `profile` | Fixed `creative-sample-real-asset-qualification-decision-finalization-v2.2`. |
| `instruction_id` | `stable_id("real_asset_qualification_decision_instruction_v22", payload)` over every other instruction field. |
| `request_id` | Exact ID of the selected Request. |
| `request_sha256` | SHA-256 of the selected canonical Request file. |
| `policy_id`, `policy_version`, `policy_document_sha256` | Exact fixed SDC-ADR-021 policy triple copied from and checked against the Request. |
| `qualifier_role` | Fixed `INDEPENDENT_QUALIFIER`. |
| `qualifier_ref_sha256` | SHA-256 of the exact separately selected Qualifier-reference file. |
| `decision_at` | Human-recorded canonical UTC second; no program-generated clock value. |
| `qualification_issue_codes` | Explicit unique tuple in the contract's canonical order. |
| `qualification_basis` | Explicit non-empty, trimmed human basis; never inferred. |
| `decision` | Exactly one of the three scoped outcomes below. |
| `qualification_scope` | Fixed `ASSET_INTAKE_ONLY`. |
| `status` | Fixed `DECISION_INSTRUCTION_RECORDED`. |
| `rights_qualification_performed` | Fixed `false`; the instruction and inspection are not a completed qualification. |
| `eligible_for_separate_manifest_design_review` | Fixed `false` in the instruction; eligibility is derived only in a completed Decision. |
| `rights_manifest_created` | Fixed `false`. |
| `current_gate` | Fixed `HUMAN_GATE`. |
| `provider_state` | Fixed `NOT_AUTHORIZED`. |
| `eligible_for_real_generation` | Fixed `false`. |
| `execution_authorized` | Fixed `false`. |
| `posts_allowed` | Fixed `0`. |
| `provider_requests` | Fixed `0`. |

The fixed policy triple is
`creative-sample-real-asset-qualification-policy / 2.0.0 /
f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031`. Every component must equal
the selected Request and the committed SDC-ADR-021 constants.

Canonical document bytes are UTF-8 without a byte-order mark, with object keys sorted, two-space
JSON indentation, unescaped Unicode where JSON permits it, and one final LF. The parser still
rejects duplicate keys before contract validation; reformatting a value-equivalent object changes
the retained file and is rejected.

The complete instruction file SHA-256 is not a field inside the instruction. The finalizer hashes
the admitted canonical bytes and records that digest in the completed Decision as
`qualifier_record_sha256`. A separately supplied digest, a mutable filename alias or a JSON object
with equivalent values but non-canonical bytes is not accepted. An opaque rename does not establish
new evidence; admission still depends on the caller's explicit path and the exact canonical bytes.

Outcome rules are closed:

| `decision` | Required issue codes | Completed-Decision effect |
|---|---|---|
| `PASS_ASSET_INTAKE_ONLY` | Empty tuple only. | `eligible_for_separate_manifest_design_review=true`; no manifest or execution permission. |
| `REJECTED` | Non-empty and contains `QUALIFIER_REJECTED_ASSET_INTAKE`. | Eligibility remains false; zero authority. |
| `NEEDS_HUMAN_REVIEW` | Non-empty and excludes `QUALIFIER_REJECTED_ASSET_INTAKE`. | Eligibility remains false; zero authority. |

Permitted issue codes, in canonical order, are:

```text
EVIDENCE_SCOPE_UNCLEAR
POLICY_REQUIREMENT_NOT_MET
QUALIFIER_REJECTED_ASSET_INTAKE
OTHER_BLOCKING_ISSUE
```

The tool does not authenticate a person's identity or decide whether the human's basis is legally
sufficient. It proves only that the exact retained Qualifier reference and exact instruction bytes
are distinct, bound to the Request and mechanically valid under the committed contract.

## Four-role and retained-record separation

The four roles are Evidence Preparer, Reviewer A, Reviewer B and Qualifier. The following six
whole-file byte identities must be pairwise distinct:

1. retained Evidence record;
2. retained Evidence Preparer reference;
3. retained Reviewer A reference;
4. retained Reviewer B reference;
5. retained Qualifier reference; and
6. complete canonical Qualifier instruction.

They must also not alias the Request, policy, upstream contracts, frozen media, provenance or
technical records. A matching SHA-256 is a byte collision and a hard stop; changing a filename
does not create independence. Conversely, distinct hashes do not by themselves prove that four
people acted independently. Confirm identity and organizational independence outside this tool.

The Reviewer contracts' `review_record_sha256` fields are canonical review-content digests, not
paths to two more retained files. The instruction itself is the Qualifier decision record; do not
look for or invent another file.

## Path layout and admission

The command admits only fully qualified local paths outside the Git repository. It rejects:

- relative, empty, UNC/network, device or extended-device paths;
- alternate data streams;
- symbolic links, junctions, mounts and all reparse points;
- hard-linked or non-regular files;
- case-folded, lexical, resolved or physical aliases;
- paths inside the repository, including repository `output/` and `tmp/`; and
- mutable alias names such as `latest`, `current` or `newest`.

The basename of `--qualifier-decision-record`, `--output` and `--decision-file` must also avoid
the outcome tokens `pass`, `rejected` and `needs`. Keep the filename opaque so a process list or
shell history cannot disclose the human conclusion.

There is one narrow enumeration exception. The existing Frozen Pack verifier may inspect the
exact tree under the explicitly supplied `--pack-root` only to reject extra members and reproduce
the fourteen technical records. It may not discover another Pack or select media. All fourteen
ordered `--media-path` values remain mandatory. No other directory is scanned.

Parents of ordinary sources may be shared, but the selected Request retains the SDC-ADR-022 rule:
its direct parent must be neither equal to, an ancestor of nor a descendant of the Frozen Pack
root or the direct parent of Evidence, Reviewer A, Reviewer B, PairCheck, retained Evidence,
retained Evidence Preparer reference, retained Reviewer A reference or retained Reviewer B
reference. The Qualifier reference and instruction may share an otherwise admissible source
parent; their paths, physical files and byte digests must still be distinct.

The Decision trust area may not intersect any source trust area. For both a new `--output` and an
existing `--decision-file`, its direct parent must already exist and be neither equal to, an
ancestor of nor a descendant of:

- the exact Frozen Pack root; and
- the direct parent of Evidence, Reviewer A, Reviewer B, PairCheck, retained Evidence, retained
  Evidence Preparer reference, retained Reviewer A reference, retained Reviewer B reference,
  Request, Qualifier reference and Qualifier instruction.

Pre-create one independent sibling Decision trust area under a separately approved procedure.
The finalizer never creates a directory, template, workspace, receipt, log, cache, temporary file
or `latest` pointer. If any source is stored directly in an aggregate private root, a Decision
directory below that root is its descendant and will be rejected. Use a genuinely
non-intersecting sibling area; do not move files into Git or silently reorganize private inputs as
a workaround.

The Decision file itself must not alias any source by path, file identity or digest. An output
target must not exist. An existing Decision must be an ordinary canonical JSON file in the same
kind of independent Decision trust area.

## Bounded reads, closure and drift checks

The implementation uses fixed, non-configurable maximum sizes:

| Artifact class | Maximum bytes per explicitly selected file |
|---|---:|
| Canonical JSON contract, Request, instruction or Decision | 1,048,576 |
| Retained private reference or evidence record | 67,108,864 |
| Frozen media object | 67,108,864 |

Environment variables, config files and CLI flags cannot raise these bounds. A file below its
bound must still match every expected size and digest.

For each source the command:

1. admits the lexical path and records the path/file identity;
2. opens the exact ordinary local file without following redirection;
3. confirms that the opened handle is the admitted file;
4. reads no more than the fixed bound and detects extra bytes;
5. hashes the bytes actually read;
6. checks the open handle and path identity again after the read; and
7. repeats the complete source-closure drift check before returning or creating output.

Any replacement, relink, hard-link count change, short or extra read, size/time/identity change,
digest mismatch or path redirection fails closed. The command never retries by selecting another
file.

Strict parsing rejects malformed UTF-8, duplicate keys, unknown fields and non-canonical JSON.
The finalizer recomputes:

- the exact fourteen-member Pack tree, object order, sizes, SHA-256 and technical evidence;
- Evidence, Reviewer A, Reviewer B and PairCheck stable IDs and canonical digests;
- retained Evidence/Preparer/Reviewer reference digests;
- exact PairCheck status `READY_FOR_SEPARATE_QUALIFICATION_REVIEW` and empty issues;
- the fixed SDC-ADR-021 policy ID, version and policy-document SHA-256;
- the Request's complete canonical bytes, ID, deadline and zero-authority state;
- the Qualifier-reference digest and instruction ID, Request binding, role separation and
  zero-authority constants; and
- for finalization or verification, the exact deterministic Decision closure.

A filename, JSON field or previously printed digest is never trusted in place of the selected
bytes.

## Time gate

`--observed-at` is required for inspection and finalization. It is an explicit caller-supplied
audit anchor in canonical UTC seconds:

```text
YYYY-MM-DDTHH:MM:SSZ
```

The program never supplies “now”, reads a clock, uses the local timezone, accepts fractional
seconds or infers a timestamp from a filesystem. The instruction supplies `decision_at`; the CLI
cannot override it.

Inspection and finalization require:

```text
request.requested_at <= instruction.decision_at <= observed_at < request.request_valid_until
```

The Request's existing 24-hour policy cap and any earlier finite Evidence expiry remain binding.
The upper expiry is exclusive. A later `observed_at`, a future decision, expired evidence or
causal-order drift stops before qualification or output.

`verify-decision` deliberately has no `--observed-at`. It uses the immutable historical times in
the Request, instruction and Decision, and reads no wall clock. Once a Decision was validly
finalized before the original exclusive deadline, later expiry does not prevent historical
verification.

## `inspect-decision-ready`

In a separately approved real operation, use inspection before considering finalization. Supply
the entire explicit closure and one audited `--observed-at`. The command performs path, byte,
strict parsing, closure, instruction and time checks, but it must not invoke
`build_real_asset_qualification_decision_v2` directly or indirectly.

Success emits only a bounded, non-secret summary with:

```text
status=READY_FOR_DECISION_FINALIZATION
rights_qualification_performed=false
```

It does not emit a Decision ID, decision outcome, basis, issue codes, SHA-256, private path,
instruction body or `QUALIFICATION_COMPLETE`. It creates no file, directory, cache, receipt or
log. Readiness means only that the exact selected bytes can be presented to the finalization
boundary; it is not itself a qualification.

## `finalize-decision`

Finalization requires a new, separately authorized invocation even after a successful inspection.
It reopens and revalidates every source; it never reuses an inspection cache. Only after all
checks, including `decision_at <= observed_at < request_valid_until`, pass may it call the existing
pure Decision builder once.

The `--output` path names one absent `.json` target in the independent Decision trust area.
Creation is exclusive:

- an existing target is a hard stop;
- no overwrite, append, truncation, in-place normalization, repair or merge is allowed;
- no `latest`, `current`, `newest`, shortcut, pointer, template or sidecar is created;
- the exact created handle is retained through write, flush, reread, strict parse and final source
  drift verification; and
- a failure never publishes partial bytes as a completed Decision.

### Failure cleanup boundary

Rollback first makes the exact newly created inode unusable through the retained descriptor and
then attempts identity-safe deletion.

- On Windows, deletion is requested through the exact open OS handle. There is no pathname
  fallback that could delete a replacement.
- On POSIX, the guarded parent directory descriptor and inode identity are compared and only that
  matching entry may be unlinked. A replacement inode is left untouched.
- Normal tested write, flush, parse and post-create failures leave no target.

If the operating system refuses final deletion after exact-inode invalidation, a zero-byte or
otherwise unparseable fail-closed remnant may remain. It is not a
`CreativeSampleRealAssetQualificationDecisionV2`; do not rename, repair, overwrite, verify or
reuse it. Arrange a separate human audit and cleanup. If neither exact-inode invalidation nor safe
deletion can be confirmed, the command emits the fixed zero-authority status
`ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED`. Immediately isolate the exact `--output` trust area;
do not verify, use, repair, overwrite or otherwise process anything in it until a separate human
audit resolves the incident. Ordinary failures continue to emit `FAILED_CLOSED`.

A successful summary may include `decision_id` and
`rights_qualification_performed=true`. It must not print the outcome, basis, issues, hashes,
paths or private contents. Record any required private audit metadata only under a separately
approved repository-external procedure; this command creates no extra record.

## `verify-decision`

Verification takes the same complete source closure plus the exact `--decision-file`. It strictly
parses the existing canonical Decision, reconstructs the Request, instruction bindings and pure
Decision closure, and requires byte-for-byte canonical equivalence.

It does not use current time, create a new Decision, rewrite an old one, fix a mismatch or emit a
receipt. The Decision remains unchanged on success or failure. Success may include `decision_id`
and `rights_qualification_performed=true`, but not its outcome, basis, issues, hashes, paths or
private contents.

Verification failure after the Request's historical deadline does not mean “expired now”; it must
identify an actual historical closure, byte or contract mismatch. Conversely, verification never
extends the original decision window or converts a late Decision into a timely one.

## Meaning of a completed Decision

All three valid outcomes set `rights_qualification_performed=true` in the completed Decision.
That is an audit fact: the v2 scoped consumer ran. It does not mean execution is authorized.

For `PASS_ASSET_INTAKE_ONLY`, the Decision derives only:

```text
eligible_for_separate_manifest_design_review=true
```

The word “separate” is a gate. No rights manifest exists, and there is still no real-generation,
Provider, POST, publication, entitlement or authorization permission. `REJECTED` and
`NEEDS_HUMAN_REVIEW` derive the same field as false. Every outcome keeps the zero-authority state
at the start of this runbook.

## Stop conditions

Stop without a Decision output on any:

- missing, extra, malformed, oversized, non-canonical or changed input;
- relative, network/device, linked, reparsed, hard-linked, aliased or intersecting path;
- unknown or duplicate JSON field;
- Pack member, ordinal, byte count, SHA-256, stable ID, role, record or cross-reference mismatch;
- PairCheck state other than exact issue-free
  `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`;
- Request that does not exactly rebuild from the selected upstream closure;
- Qualifier instruction that does not bind the exact Request and Qualifier reference;
- repeated or aliased retained records or role identity;
- invalid outcome/issue combination or missing human basis;
- `decision_at` before the Request, after `observed_at`, or at/after exclusive Request expiry;
- `observed_at` at/after expiry for inspection or finalization;
- existing or mutable-alias output target;
- any TOCTOU or rollback-identity uncertainty;
- any nonzero execution, publication or Provider state;
- any request to infer or override the Qualifier's conclusion;
- any request to create a rights manifest or translate two v2 reviews into 28 v1 records; or
- any attempt to read or write repository `output/`, `tmp/`, a registry, Ledger or migration.

Never continue with an override, waiver, repair or “best effort” option.

## Prohibited operations

This boundary must not:

- run against real private records during this synthetic development PR;
- generate a rights manifest or call the v1 rights qualification path;
- synthesize 28 v1 reviewer records;
- modify entitlement or authorization state;
- start Runtime, Worker, Provider, PostgreSQL or Temporal;
- access Ark or another console;
- read an API Key;
- use a network, upload, POST or Provider request;
- purchase, recharge or claim a trial;
- write an Atomic Ledger entry or migration;
- create a directory, template, cache, log, receipt, temp file or mutable alias; or
- read or modify repository `output/` or `tmp/`.

## Synthetic offline verification

The implementation PR must use only synthetic temporary fixtures and non-integration offline
checks. Test at least:

- exact CLI surface with only the three named commands;
- absence of CLI decision, basis, issue-code and decision-time inputs;
- strict v2.2 instruction parsing, content-derived ID, canonical bytes, Request/Qualifier binding
  and whole-file `qualifier_record_sha256` derivation;
- all three decision outcomes and issue-code rules;
- `inspect-decision-ready` readiness without any Decision-builder call or filesystem write;
- explicit `--observed-at`, absence of clocks/defaults and
  `requested_at <= decision_at <= observed_at < request_valid_until`;
- historical `verify-decision` after the deadline with no observed time or clock;
- exact explicit-path closure, fourteen media occurrences and rejection of discovery, globs and
  mutable aliases;
- repository-external path enforcement plus UNC/device, link, junction, reparse, hard-link,
  alternate-data-stream, alias and intersecting-parent rejection;
- fixed read bounds for every artifact class;
- strict JSON, complete stable-ID/SHA-256 reconstruction and six retained-record non-aliasing;
- pre-read, opened-handle, post-read and pre-output TOCTOU failures;
- exclusive create-new output, existing-target refusal and exact-handle safe rollback;
- summary redaction of outcomes, basis, issues, paths, digests and private contents;
- zero-authority state for PASS, REJECTED and NEEDS_HUMAN_REVIEW;
- absence of manifest/v1 conversion, Runtime, Provider, Ark, database, Ledger, migration,
  entitlement, authorization and network dependencies; and
- byte identity of the 55 pre-existing Schemas, compatibility of all existing contracts and the
  existing pure Finalizer Python API, with exactly one append-only instruction Schema making 56.

Do not start services or contact paid or remote systems. Complete a P0/P1/P2 audit before opening
the independent Draft PR.

## Later stages remain separate

After this PR is reviewed and merged, a user may separately approve a real-path inspection. A
later explicit approval may authorize finalization of one exact instruction and destination.
Neither approval authorizes a rights manifest, entitlement, publication or execution.

Even a real `PASS_ASSET_INTAKE_ONLY` Decision merely opens a separate manifest-design review gate.
A manifest consumer needs its own ADR, versioned contract, policy review, offline tests and
independent PR. Any entitlement or authorization bridge is another later stage. Do not infer
approval from a successful Decision or from `rights_qualification_performed=true`.
