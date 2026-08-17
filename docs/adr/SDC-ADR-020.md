# SDC-ADR-020: Pack-level offline human review v2

- **Status:** Proposed
- **Date:** 2026-08-17
- **Version:** V02

## Context

Creative Sample Real Asset Intake v1 deliberately requires two independent, byte-bound reviews
for each of fourteen assets. Its 28 records make every approval, disagreement and expiry visible,
and its committed contracts and schemas are now an audit boundary. That boundary must remain
immutable: changing a v1 field, default, validation rule or schema to improve usability would make
old records ambiguous and weaken the byte-compatibility guarantees already relied upon by tests
and retained private evidence.

The v1 shape is nevertheless a poor default user experience for a homogeneous candidate pack. It
asks each reviewer to repeat the same copyright basis, likeness/privacy basis, territory, use
scope and validity across fourteen records. It also exposes JSON syntax, hashes and UTC formatting
as manual work. Repetition does not create independent judgment; it creates transcription risk.

This ADR adds a separate v2 review path. It reduces repeated input while preserving two real human
decisions, exact frozen-byte coverage and fail-closed behavior. It does not relax v1, migrate v1
records or make a reviewed pack executable.

## Decision

V1 remains supported and unchanged as the per-asset audit profile. V2 is append-only: it uses new
contract and schema names, new document types and a separate offline console/finalization flow.
No v2 implementation may reinterpret, rewrite or regenerate an existing v1 rights review,
rights manifest, qualification result or frozen pack.

The v2 evidence model has three levels:

1. **One `CreativeSampleRealAssetRightsEvidenceBundleV2`.** The operator records the normalized
   copyright, likeness, privacy, territory, use scope and validity basis once and explicitly binds
   the declaration to the exact frozen pack and all fourteen member byte identities.
2. **Two `CreativeSampleRealAssetHumanPackReviewV2` documents.** `REVIEWER_A` and `REVIEWER_B`
   each inspect all fourteen exact members and the same Pack-level evidence bundle, make their own
   six Pack-level approval choices and fourteen content-role choices, and submit one review.
   Reviewer identity/reference and review-record identity must remain distinct; one person's
   response cannot be copied, promoted or synthesized into the other role.
3. **`RealAssetReviewExceptionV2` only when needed.** A reviewer attaches an exception to the
   exact `RealAssetHumanFindingV2` when that member is not covered by the Pack declaration or has a
   provenance, copyright, likeness, privacy, content-role, territory or use-scope issue. Absence of
   an exception is never inferred to mean approval unless the reviewer has affirmatively completed
   every required Pack-level decision and confirmed review of the full fourteen-member closure.

The v2 compiler validates exact pack identity, ordered member coverage, reviewer separation,
review completeness, evidence consistency, expiry and exception references. The mechanical A/B
closure is a `CreativeSampleRealAssetReviewPairCheckV2`, whose only states are `INCOMPLETE`,
`DISAGREEMENT` and `READY_FOR_SEPARATE_QUALIFICATION_REVIEW`. The last state is a review handoff,
not qualification. Any missing member, missing decision, rejected decision, reviewer collision,
disagreement, invalid/expired evidence, unknown field, digest drift or malformed document remains
`HUMAN_GATE`.

## Static local console boundary

The human interface is a static-file bridge, not a web application or service. A trusted Python
preparation step reads an explicit frozen-pack path, verifies it and writes a new local workspace
containing bounded JSON plus committed HTML/CSS/JavaScript assets. The `EVIDENCE` workspace is
prepared first. Only after its draft becomes a canonical evidence bundle may separate invocations
create `REVIEWER_A` and `REVIEWER_B` workspaces; each reviewer context binds that exact bundle ID
and document SHA-256, and its role is fixed rather than selected in the browser. Each workspace
contains exactly `index.html`, `app.js`, `style.css`, `review-context.json` and
`review-context.js`. The operator opens the HTML with `file://`. There is no HTTP listener,
`localhost`, embedded server, remote script, CDN, telemetry, analytics, upload or network fallback.

The browser layer may display only the prepared local review projection and collect human input.
It may calculate a convenience SHA-256 over a human-selected file in memory, but that value remains
untrusted until Python re-reads the private record. The browser is not trusted to verify the frozen
pack, choose approval values, establish UTC time, sign evidence or publish a final contract. It
produces a local candidate response through the explicit static-file handoff defined by the
implementation. It must not write into the frozen pack, source evidence, Git repository,
`output/` or `tmp/`.

Browser-originated values remain untrusted drafts. They intentionally omit stable IDs,
`reviewed_at` and review-record digests and cannot be supplied directly to the pair closure. The
Python finalization boundary reloads the original frozen pack and prepared binding, rejects
duplicate JSON keys and unexpected fields, validates every contract and explicit UTC value,
derives canonical IDs and record digests, and publishes a new result with no-replace semantics. A
partially written, stale, mismatched or ambiguous result is not repaired or treated as a review.

The operational boundary is split between `sdc.human_review_console` and
`sdc.human_review_finalizer`. The finalizer re-hashes the private evidence or reviewer record named
on its command line and requires that digest to equal the human draft. It also requires the exact
prepared workspace, verifies its five-file closure and context digest before and after finalizing,
and rejects a review workspace not bound to the supplied canonical evidence bundle. Its CLI
mechanically captures current UTC seconds for finalized reviews and PairChecks; the corresponding
library APIs take explicit UTC values so deterministic tests never depend on a wall clock. Neither
path chooses an approval, decision, exception or rights basis for a human.

The pure contract function `finalize_real_asset_review_pair_v2` checks the canonical evidence and
two review documents only. It is deterministic and intentionally performs no filesystem I/O, so
its result alone does not prove that retained private records are still available. The trusted
`check-pair` CLI uses `check_human_review_pair` as the operational boundary: it requires three
distinct current files for the evidence record, Reviewer A record and Reviewer B record, re-hashes
each against its bound digest, then performs the pure structural PairCheck. Missing, aliased or
drifted retained records publish no PairCheck. Retained records and finalized outputs must also
remain outside the frozen Pack, Git and every prepared Console workspace; workspace files are a
verified static bridge, not private evidence or an output container.

A retained-record SHA-256 proves only the identity and continued availability of the supplied
bytes. It does not authenticate a person, establish that two people acted independently, or
interpret the record's meaning. The operator must ensure that the two reviewer records are
created and controlled by the two named humans and are not copies of Console, contract or other
unrelated files. Known files from the workspace being finalized are rejected mechanically, but
semantic reviewer authentication remains an explicit human and organizational control.

## Zero-authority result

Every v2 preparation, candidate response and finalized review remains:

- `HUMAN_GATE`;
- `NOT_AUTHORIZED`;
- `execution_authorized=false`;
- `posts_allowed=0`; and
- `provider_requests=0`.

Neither the static console nor the Python finalizer imports or invokes Runtime, Worker, Provider,
PostgreSQL, Temporal, Ark, entitlement, authorization or Atomic Ledger behavior. It must not read
an API Key, start a service, access a console, issue HTTP, buy resources, recharge or claim a
trial. Positive entitlement and authorization registries remain empty.

This delivery intentionally stops after producing and verifying inert v2 review records. It does
not build a `CreativeSampleRealAssetRightsManifest`, call v1 rights qualification, derive a real
asset revision, or create any other execution/publishing authority. A v2 pack review is not
automatically expanded into 28 v1 records. If a later design needs a reviewed conversion, that
conversion requires a separate versioned contract, explicit policy decision and independent PR;
fabricating v1 reviewer records from pack-level input is forbidden.

## Consequences

The normal homogeneous-pack path falls from 28 repetitive forms to one pack evidence declaration,
two independent reviews and only the exceptions actually found. Exact member identity and two
human decisions remain visible, while syntax, hashing, binding and structural checks move to the
trusted local Python boundary.

V1 and all pre-v2 schemas remain byte-compatible. V2 adds code, schemas, static assets,
documentation and offline tests only. Its usability improvement cannot be cited as weaker review
for real-person, third-party or otherwise high-risk material; policy may still require the v1
per-asset profile or another stricter process.

The static console deliberately forgoes server features and browser persistence conveniences.
Operators exchange local candidate files and run an explicit finalizer, which is less seamless
than a hosted UI but keeps private media and evidence off the network and makes the trust boundary
auditable.
