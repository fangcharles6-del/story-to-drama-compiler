# Creative Sample pack-level human review v2

This runbook prepares and finalizes two independent, purely local human reviews of one already
frozen Creative Sample Real Asset Pack. It reduces repeated entry; it does not reduce the review
boundary and does not authorize generation, publication or Provider access.

## Permanent safety state

Every step in this runbook must retain:

```text
HUMAN_GATE
NOT_AUTHORIZED
execution_authorized=false
posts_allowed=0
provider_requests=0
```

Do not provide an API Key, account credential, Ark/console capture, Provider task, positive
entitlement or authorization entry, Runtime/Worker state, Temporal history, PostgreSQL export or
Atomic Ledger data. Do not start a service or local HTTP server. Do not use `localhost`, a mapped
network drive, cloud-sync location, browser extension, remote script, CDN or upload.

This flow reads only explicit local paths. Frozen media, source/provenance records, rights evidence,
reviewer identity records and review results stay outside Git. Never place them in the repository,
`output/` or `tmp/`.

## Preconditions

- The exact fourteen-member pack has already been frozen and passes the existing full local pack
  verifier without drift.
- The pack manifest remains `FROZEN_UNREVIEWED / HUMAN_GATE` and grants no authority.
- One private pack-level rights evidence declaration is available. It states only facts supported
  by retained evidence and identifies the exact territory, use scope and validity boundary.
- Reviewer A and Reviewer B are two real, distinct people able to inspect all fourteen frozen
  assets and the retained evidence independently.
- The destination workspace and final result paths do not exist. There is no overwrite, resume,
  merge, repair or `--force` path.

Technical admission is not a rights conclusion. Generated-looking content, a valid PNG/WAV,
successful SHA-256 verification or the absence of an obvious real person does not justify an
approval. Stop if the actual retained evidence is unavailable or unclear.

## Local workflow

The implementation separates static workspace preparation from trusted Python finalization. Use
only the committed command-line entry points and exact argument names listed in the command
reference below. Do not substitute a generic web server or edit generated bindings by hand.

### 1. Prepare the evidence workspace

Prepare only the `EVIDENCE` workspace at this point. Preparation must:

1. load the explicit frozen pack path and re-run complete pack verification;
2. bind the pack ID, manifest identity and all fourteen ordered member SHA-256/size/role/technical
   summaries into the reviewer projection;
3. pre-bind the evidence workspace kind and context digest, with no human answers filled;
4. copy only `index.html`, `app.js`, `style.css`, `review-context.json` and
   `review-context.js`; and
5. publish new-only, leaving the frozen pack and evidence records unchanged.

After preparation, verify the reported workspace identity and paths. If the destination existed,
the source changed during preparation, a member is missing, the pack is not exact, or any output
is partial or ambiguous, stop and preserve the evidence for inspection.

### 2. Prepare and finalize the Pack-level evidence once

Open the `EVIDENCE` workspace's `index.html` using `file://`. Enter only facts supported by the
retained private evidence: its record SHA-256, copyright/likeness/privacy bases, territory, use
scope and `valid_until`. The optional local file picker calculates a SHA-256 in browser memory; it
does not upload or copy the selected record. Export the canonical evidence draft and pass it to
the trusted Python `finalize-evidence` operation. The resulting
`CreativeSampleRealAssetRightsEvidenceBundleV2` supplies the bundle ID used by both reviewers.

The browser draft is not the bundle. It has no stable bundle ID and cannot establish approval.

#### Evidence v2.1 preparation readiness

This is operator guidance for preparing the existing v2 evidence fields; “v2.1” does not name a
new contract, change qualification semantics or add an approval path. Before typing, collect one
retained Pack-level evidence record whose statements can be traced to the responsible people and
source documents below. The record must describe the exact frozen Pack, distinguish fact from
uncertainty and preserve references to the supporting private files.

| Field | Required source category | Obtain it from | Format-only example (not a factual answer) |
|---|---|---|---|
| `evidence_record_sha256` | Byte identity of the completed, retained Pack-level evidence record | Select the actual record maintained by the rights coordinator or accountable project owner; let the local file picker compute its SHA-256 | `<64 lowercase hexadecimal characters>` |
| `copyright_basis` | Authorship, ownership, licence and applicable-use evidence for every included image and audio asset | The creator or rights owner, licensing administrator and the retained creation records, licence terms, agreements or grants that applied when each asset was made or acquired | `依据：[记录/许可类型与引用]；权利主体：[主体]；许可行为及限制：[范围]` |
| `likeness_basis` | Evidence covering depicted persons, character identity, performers, voices and any imitation or publicity-right concern | The depicted person or performer where applicable, producer/rights owner, and retained releases, consents, casting/voice records or documented synthetic-character provenance | `对象类别：[类别]；依据：[同意/来源记录引用]；限制：[限制或待决项]` |
| `privacy_basis` | Personal-data source, consent or other documented processing basis, including any applicable retention/use constraints | The data subject where applicable, privacy owner or accountable producer, and retained consent, privacy assessment, collection/source and retention records | `数据类别：[类别]；处理依据：[文件引用]；用途及保留限制：[限制]` |
| `territory` | Express geographic extent of the relevant rights | The licensor/rights owner or responsible legal/rights reviewer, using the governing agreement, grant or rights schedule | `[协议原文支持的地区表达]` |
| `use_scope` | Express permitted media, channels, audience, publication/commercial status and modification or distribution limits | The licensor/rights owner or responsible legal/rights reviewer, using the governing licence, release, project grant or rights schedule | `[允许用途]；[允许渠道]；[禁止或限制事项]` |
| `valid_until` | Express term or expiry evidence for every relied-upon right | The rights administrator, licensor or responsible legal/rights reviewer, using the controlling term clause or expiry schedule | `YYYY-MM-DDTHH:MM:SSZ` or `PERPETUAL` only when the retained evidence expressly says so |

The examples show shape only. Do not copy them as answers, turn a placeholder into a conclusion,
or infer missing scope from another field. A technical validation record can establish media
format, duration, dimensions or byte identity, but cannot establish ownership or permission. A
filename, folder name, generation prompt, tool label, SHA-256, source ledger entry or visual/audio
inspection also cannot by itself prove copyright, likeness/privacy permission, territory, use
scope or duration. “Looks fictional”, “sounds synthetic”, “generated locally” and “no obvious
personal data” are observations, not substitutes for retained rights evidence.

The Evidence UI has only two mechanical readiness states:

- **Missing basis — stop.** A required source or field is missing, unclear, conflicting,
  unsupported or known to be expired, or the referenced record is unavailable. Do not invent
  text, export a candidate for finalization or proceed to reviewer preparation.
- **Field form complete — untrusted draft may be exported.** All seven fields pass only the
  browser's deterministic syntax checks. The browser does not verify that a manually entered
  digest still identifies an available record, and it does not compare `valid_until` with the
  current time. The operator must separately stop for an unavailable record or known expiry.
  Export is only a data handoff to the trusted finalizer; it is not factual verification, human
  approval, rights qualification or execution authorization.

Neither state permits the UI to interpret evidence or recommend a rights conclusion. If the
responsible person or controlling document cannot supply an answer, remain in the first state and
stop. The finalizer continues to perform only the existing structural and byte-binding checks.

### 3. Prepare two evidence-bound reviewer workspaces

After `finalize-evidence` produces the canonical bundle, prepare the `REVIEWER_A` and `REVIEWER_B`
workspaces using that exact file. Preparation reloads the frozen Pack and evidence contract,
rebuilds the evidence from the Pack, and binds the evidence bundle ID and canonical document
SHA-256 into each review context. A reviewer workspace cannot be prepared without `--evidence`,
and an evidence workspace must not accept one.

Every downloaded draft carries its prepared `review_context_sha256`. Reviewer drafts additionally
carry the exact `evidence_bundle_id` and `evidence_bundle_sha256`; these are bindings, not editable
human answers.

Do not reuse reviewer workspaces made for an earlier evidence draft or bundle. Do not edit
`review-context.json` or `review-context.js` to change the evidence ID, digest or reviewer role.

### 4. Reviewer A completes one independent review

Reviewer A opens only the generated local HTML file using `file://`; no server is needed. They
must inspect every image, play every audio member, inspect the pack-level evidence declaration and
affirmatively mark all fourteen members as viewed.

Reviewer A then makes each required approval choice. They add a per-asset exception for every
member not fully covered by the pack declaration or presenting a content-role, copyright,
likeness, privacy, territory, use-scope, validity or other blocking concern. For each exception,
they select every applicable failed gate and write the actual finding without inventing rights
facts. `APPROVED` requires all six Pack choices and fourteen content-role choices to be true with
no exception. `REJECTED` requires a failed choice and a human-written rejection reason. They must
reject rather than approve when any required basis is unknown, conflicting or expired.

The console must not suggest, preselect, infer or auto-fill an approval or decision. Reviewer A
exports only their own local candidate response using the console's defined static-file handoff.
The draft deliberately has no `reviewed_at`, `review_record_sha256` or `review_id`.

### 5. Reviewer B completes a separate review

Reviewer B repeats the same process in the B workspace without opening Reviewer A's response or
copying their selections. Reviewer B must inspect the same exact fourteen byte identities and
pack-level evidence but reaches an independent conclusion. A common operator must not convert,
duplicate or rename one response into the other reviewer role.

Different review times and records are expected. Reviewer identity/reference and final review
record identity must be distinct. Any role collision, missing member confirmation, missing answer
or malformed response is a hard stop.

### 6. Finalize with trusted Python

Run finalization only after the appropriate human has exported a complete local candidate. The
finalizer, not browser JavaScript, is responsible for trusted parsing, frozen-pack re-verification,
workspace binding, reviewer-role enforcement, canonicalization, SHA-256 derivation, explicit UTC
validation and new-only publication.

The `--workspace` value is mandatory for evidence and review finalization. The finalizer verifies
the complete five-file workspace and its context digest before and after reading the draft. Review
finalization additionally requires that the workspace, draft and `--evidence` file all bind the
same canonical bundle ID and SHA-256. No finalizer command may write its output under any Console
workspace; parent-chain marker checks enforce that separation.

Finalize A and B independently. Never pass both candidates through a command that fills missing
answers or reconciles disagreement. Do not manually insert a timestamp or digest merely to make a
record validate.

After both reviews are finalized, run `check-pair`. Its strongest result is
`READY_FOR_SEPARATE_QUALIFICATION_REVIEW`; this means only that the two inert records form a clean
pair. Any rejected decision, exception, disagreement, expiry, stale workspace, changed pack,
duplicate reviewer, duplicate record identity or unavailable retained evidence remains
`HUMAN_GATE`.

## Command and artifact reference

All paths below must be absolute, local and outside every Git worktree. Retained private records
and finalized outputs must also remain outside the frozen Pack and every Console workspace. Each
Console workspace and its frozen Pack must share a drive so the media links remain relative. The
workspace and finalized-output parents must already exist; each generated workspace directory and
final JSON file must not exist. Replace the example values with the private local paths actually
approved for this Pack.

```powershell
$packRoot = "C:\PRIVATE\frozen\<real_asset_pack_id>"
$workspaceParent = "C:\PRIVATE\human-review-v2"
$finalizedParent = "C:\PRIVATE\human-review-v2-finalized"
$evidenceWorkspace = Join-Path $workspaceParent "human-review-console-v2-<real_asset_pack_id>-evidence"
$reviewAWorkspace = Join-Path $workspaceParent "human-review-console-v2-<real_asset_pack_id>-reviewer-a"
$reviewBWorkspace = Join-Path $workspaceParent "human-review-console-v2-<real_asset_pack_id>-reviewer-b"
```

Prepare only the isolated evidence workspace:

```powershell
uv run python -m sdc.human_review_console prepare `
  --pack-root $packRoot `
  --output-parent $workspaceParent `
  --workspace-kind EVIDENCE
```

For Pack ID `<real_asset_pack_id>`, the complete flow eventually creates these directories in
order:

```text
human-review-console-v2-<real_asset_pack_id>-evidence
human-review-console-v2-<real_asset_pack_id>-reviewer-a
human-review-console-v2-<real_asset_pack_id>-reviewer-b
```

Each contains exactly five files: `index.html`, `app.js`, `style.css`, `review-context.json` and
`review-context.js`. Open only `index.html` directly from the filesystem. Do not run a local
server such as `python -m http.server`, use an IDE preview server or rewrite the URL to
`http://localhost`.

The evidence workspace downloads
`rights-evidence-bundle-v2-draft-<real_asset_pack_id>.json`. Keep that download and the underlying
private evidence record outside Git, then finalize it:

```powershell
$evidenceDraft = "C:\PRIVATE\review-drafts\rights-evidence-bundle-v2-draft-<real_asset_pack_id>.json"
$evidenceRecord = "C:\PRIVATE\rights-evidence\pack-evidence-record"
$evidenceOutput = Join-Path $finalizedParent "rights-evidence-bundle-v2.json"

uv run python -m sdc.human_review_finalizer finalize-evidence `
  --pack-root $packRoot `
  --workspace $evidenceWorkspace `
  --draft $evidenceDraft `
  --evidence-record $evidenceRecord `
  --output $evidenceOutput
```

The finalizer verifies that the private record's SHA-256 equals the draft, re-verifies the Pack,
re-verifies the exact evidence workspace and context digest, derives `bundle_id` and publishes a
new canonical `CreativeSampleRealAssetRightsEvidenceBundleV2`.

Now prepare the reviewer workspaces. Both must bind the canonical evidence output explicitly:

```powershell
uv run python -m sdc.human_review_console prepare `
  --pack-root $packRoot `
  --output-parent $workspaceParent `
  --workspace-kind REVIEWER_A `
  --evidence $evidenceOutput

uv run python -m sdc.human_review_console prepare `
  --pack-root $packRoot `
  --output-parent $workspaceParent `
  --workspace-kind REVIEWER_B `
  --evidence $evidenceOutput
```

The prepared contexts display and bind the evidence bundle; do not paste another ID into the form
or give either reviewer the other person's draft.

The reviewer workspaces download
`human-pack-review-v2-draft-<real_asset_pack_id>-reviewer_a.json` and the corresponding
`...-reviewer_b.json`. Each reviewer also retains a distinct private reviewer record whose
SHA-256 is the `reviewer_ref_sha256` they entered. Finalize the two records independently:

```powershell
$reviewADraft = "C:\PRIVATE\review-drafts\human-pack-review-v2-draft-<real_asset_pack_id>-reviewer_a.json"
$reviewBDraft = "C:\PRIVATE\review-drafts\human-pack-review-v2-draft-<real_asset_pack_id>-reviewer_b.json"
$reviewARecord = "C:\PRIVATE\reviewer-records\reviewer-a-record"
$reviewBRecord = "C:\PRIVATE\reviewer-records\reviewer-b-record"
$reviewAOutput = Join-Path $finalizedParent "human-pack-review-v2-reviewer-a.json"
$reviewBOutput = Join-Path $finalizedParent "human-pack-review-v2-reviewer-b.json"

uv run python -m sdc.human_review_finalizer finalize-review `
  --pack-root $packRoot `
  --workspace $reviewAWorkspace `
  --evidence $evidenceOutput `
  --draft $reviewADraft `
  --reviewer-record $reviewARecord `
  --expected-role REVIEWER_A `
  --output $reviewAOutput

uv run python -m sdc.human_review_finalizer finalize-review `
  --pack-root $packRoot `
  --workspace $reviewBWorkspace `
  --evidence $evidenceOutput `
  --draft $reviewBDraft `
  --reviewer-record $reviewBRecord `
  --expected-role REVIEWER_B `
  --output $reviewBOutput
```

The CLI captures one current local-machine UTC second at invocation. The finalizer validates and
binds that value while performing strict draft, role, private-record and frozen-Pack checks; a
failed check publishes nothing. It derives the review-record SHA-256 and stable review ID but does
not choose or alter any human answer. The library API accepts an explicit `reviewed_at` solely for
deterministic testing.

Finally, create the inert A/B PairCheck:

```powershell
$pairOutput = Join-Path $finalizedParent "human-review-pair-check-v2.json"

uv run python -m sdc.human_review_finalizer check-pair `
  --pack-root $packRoot `
  --evidence $evidenceOutput `
  --evidence-record $evidenceRecord `
  --reviewer-a $reviewAOutput `
  --reviewer-a-record $reviewARecord `
  --reviewer-b $reviewBOutput `
  --reviewer-b-record $reviewBRecord `
  --output $pairOutput
```

Before the structural comparison, trusted `check-pair` requires three distinct current retained
files, re-reads them and verifies their SHA-256 values against the evidence and reviewer
contracts. All three records must remain outside Git, the frozen Pack and every Console workspace.
A missing, linked, aliased, misplaced, changed or digest-mismatched record stops without output.
It then mechanically captures its UTC evaluation second and writes a new
`CreativeSampleRealAssetReviewPairCheckV2`.

SHA-256 establishes byte identity and current availability only. It does not prove that a record
was authored by a human, authenticate the reviewer's identity, establish A/B independence, or
interpret record semantics. The operator must keep Reviewer A and Reviewer B records under the
control of the corresponding two humans and must not substitute copies of Console files,
contracts or unrelated local files. The finalizer rejects known aliases from the workspace being
finalized; reviewer identity and independence remain explicit human and organizational controls.

The pure `finalize_real_asset_review_pair_v2` contract function checks only the canonical
documents and has no filesystem dependency. That is useful for deterministic structural tests,
but does not prove retained-record availability; operational use must go through the trusted CLI
above. Acceptable structural output is one of `INCOMPLETE`, `DISAGREEMENT` or
`READY_FOR_SEPARATE_QUALIFICATION_REVIEW`; all three retain zero authority. Do not rename the last
state to `APPROVED`, and do not continue to qualification in this PR.

| Artifact | Meaning |
|---|---|
| Console draft | Untrusted local human input; no stable ID, review time or review-record digest |
| `CreativeSampleRealAssetRightsEvidenceBundleV2` | One Pack-level `EVIDENCE_CANDIDATE`; not approval |
| `CreativeSampleRealAssetHumanPackReviewV2` | One role-bound `REVIEW_COMPLETE` human record; still `HUMAN_GATE` |
| `CreativeSampleRealAssetReviewPairCheckV2` | Mechanical A/B closure report; trusted CLI also re-hashes all three retained records; still not a rights manifest or qualification |

## What finalization does not do

Successful local verification means only that the inert v2 review records are structurally valid
and bound to the same frozen pack. This PR must not:

- generate a v1 `rights-manifest.json`;
- invoke `build_real_asset_rights_manifest`, `qualify_real_asset_candidate_pack` or another rights
  qualification path;
- synthesize or automatically expand the two pack reviews into 28 v1 per-asset reviews;
- derive a qualified real-asset revision or change a sample/specification identity;
- add an entitlement/authorization registry entry or ledger claim; or
- enable Runtime, Worker, Provider, PostgreSQL, Temporal, Ark, HTTP or POST behavior.

A future use of the reviews requires a separately designed and approved consumer. Until then the
review output is private, local evidence at a human gate only.

## Stop conditions

Stop without repair or fallback on any of the following:

- missing, extra, renamed, linked or changed frozen member;
- pack, manifest, evidence, workspace or candidate digest mismatch;
- existing destination or unclear publication result;
- unknown/duplicate JSON field, malformed response or browser-originated binding change;
- fewer than fourteen explicit viewed confirmations from either reviewer;
- missing decision, reviewer collision, copied record or untraceable reviewer/evidence reference;
- unavailable, aliased or SHA-drifted retained evidence/Reviewer A/Reviewer B record;
- retained record or finalized output placed inside the frozen Pack or a Console workspace;
- any exception, rejection, disagreement or expired validity;
- any request to auto-answer, infer rights, backfill v1, generate a rights manifest or qualify;
- any attempt to read a Key, access Ark, start a service, use localhost/network storage or upload
  private material; or
- any nonzero execution authority, posts allowance or Provider-request counter.

Retain the original frozen pack and private evidence unchanged. A corrected human response is a
new candidate and a new result path; it never overwrites the failed one.
