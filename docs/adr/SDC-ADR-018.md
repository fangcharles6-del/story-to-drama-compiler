# SDC-ADR-018: Evidence-bound Live Canary execution boundary

- **Status:** Proposed
- **Date:** 2026-08-15
- **Version:** V01

## Decision

The first supported Ark execution path will be a dedicated, evidence-bound, one-POST Canary. It
will remain narrower than the normal `DramaWorkflow`: one frozen Run, one Job, Attempt 1, text-only
input, 9:16, 1080p, 24 fps, 4000 ms, `generate_audio=false`, exact model
`doubao-seedance-2-0-260128`, region `cn-beijing`, and no Provider or model fallback. The approved
cost must cover the reviewed cost floor, may not exceed CNY 15, and is a review boundary rather
than a Provider-side billing guarantee.

This ADR fixes the interfaces, state transitions, trust order and test obligations for later
implementation. It does not add an entitlement object, approve an authorization, connect the
ADR-017 guard to runtime, read a Key, start a service or issue an Ark request. Until all follow-up
deliveries are approved and merged, the existing Ark Worker and every Ark `RuntimeActivities`
entrypoint remain unconditionally disabled.

## Positive authority chain

Live submission requires all of the following independent, positive anchors. A digest found in
the artifact that it purports to authenticate is never an independent anchor.

1. A Git-reviewed execution-day capability/pricing bundle under ADR-016.
2. A separate Git-reviewed execution-day entitlement bundle defined below.
3. The exact evidence-bound plan, frozen execution and request fingerprint.
4. A Git-reviewed runtime-release manifest, Task Queue and durable ledger/deployment identity.
5. An inert ADR-017 authorization candidate that binds items 1-4 and expires within every
   evidence window.
6. A separate Git-reviewed authorization-registry entry for the exact canonical candidate digest.
7. A successful PostgreSQL claim made with database time before any secret value or socket write.

Registry lookup precedes artifact reads. Artifact and CAS verification precedes database claim.
Database claim precedes Key access. Key access and a final database-time expiry check precede the
single socket write. No later phase may compensate for a failed earlier phase.

## Entitlement EvidenceBundle profile

The new `ark-canary-entitlement-v1` profile is separate from the capability/pricing profile. It
contains exactly two distinct objects and one `FRESH` capture, with no predecessor or origin:

- `evidence/entitlement.pdf`, role `entitlement.evidence`, media type `application/pdf`, containing
  only a sanitized, flattened read-only console observation; and
- `snapshots/entitlement.json`, role `entitlement.snapshot`, media type `application/json`, with
  document type `sdc.ark-canary-entitlement-snapshot` and schema version `1.0.0`.

The single capture has ID `entitlement`, kind `official-console-entitlement`, acquisition
`FRESH`, `source_updated_at=null`, and exactly those two member paths. The bundle `created_at`
equals the capture time and the bundle deadline equals the snapshot deadline. The PDF is bounded,
unencrypted and contains no attachment, form, JavaScript, open action or external URI action. These
mechanical checks do not replace independent visual privacy review.

The snapshot binds:

- document type, profile and schema version;
- provider `volcengine_ark`, service `ark-video-generation`, exact model
  `doubao-seedance-2-0-260128`, region `cn-beijing` and operation
  `contents.generations.tasks.create`;
- observed provider state `ENABLED` and conclusion `PASS_ENTITLEMENT_ONLY`;
- a domain-separated `account_scope_sha256` derived during independent review from the stable
  Provider account, subaccount and project scope without publishing those raw identifiers;
- a domain-separated `credential_binding_sha256` derived from the approved secret-store resource
  locator and immutable version metadata, never from or including the Key value;
- canonical console URL, observation/capture times, exclusive validity deadline and evidence
  object digest.

The canonical console URL uses HTTPS, the exact reviewed Volcengine console host and one
allowlisted route. It contains no user information, unusual port, query or fragment. The PDF limit
is 16 MiB and the strict UTF-8 snapshot limit is 64 KiB; duplicate JSON keys and non-finite numbers
are rejected.

Canonical JSON in this profile means UTF-8 JSON with lexicographically sorted object keys, no
insignificant whitespace, `ensure_ascii=false`, normalized UTC timestamps and no duplicate keys or
non-finite numbers. The account input has exactly the keys `account_id`, `subaccount_id` and
`project_id`; each value is the stable Provider identifier string or `null`, never a display name.
With a reviewer-controlled 32-byte random salt, its digest is
`SHA256("sdc:volcengine-account-scope:v1\0" || canonical_scope_json || "\0" || private_salt)`.

Credential metadata has exactly `secret_store`, `resource_locator` and `immutable_version` string
keys and uses
`SHA256("sdc:ark-credential-binding:v1\0" || canonical_credential_json || "\0" || private_salt)`.
The independent reviewer retains the stable salt outside Git, CAS, CLI arguments and logs so
renewals can be compared without disclosing the identifiers. The raw credential locator also
remains outside the repository. Both digests are treated as sensitive pseudonymous metadata.
Matching them does not prove that the secret value belongs to the account, so deployment review
must independently establish that relationship.

The evidence excludes names, email, phone, balance, bills, quota details, existing Key labels or
masked values, cookies, headers, request/task IDs, DOM/HAR dumps and the Key itself. It proves only
the reviewed post-state for the recorded account scope, model and region. It is not a
LiveAuthorization, billing guarantee or cryptographic proof that an arbitrary Key belongs to that
scope.

The profile validity is no later than the earliest of its declared source boundary, four hours
after capture, and `23:59:59+08:00` on the capture date. `valid_until` is exclusive. Import, copy,
review, registry commit and clock conversion may shorten but never extend it. Execution therefore
requires `captured_at <= reviewed_at <= db_now < valid_until`. A future-dated capture or review,
or equality at the deadline, fails closed. Renewal requires a new read-only observation, new
bundle and new reviewed registry entry; repackaging or another review cannot renew an old bundle.

A new positive registry entry will bind exactly one entitlement bundle ID, logical-tree digest,
snapshot contract digest, raw evidence digest, provider, model, region, operation,
account-scope digest, credential-binding digest, capture time, `reviewed_at` and `valid_until`.
Bundle, tree, snapshot, raw-evidence and derived registry-entry identities must be unique. A later
capture may intentionally retain the same account-scope and credential-binding digests, but it
must have new evidence and cannot extend its predecessor. Lookup of an exact caller-selected
bundle ID happens before manifest or CAS reads; there is no "latest" auto-selection. The
`entitlement_anchor_sha256` already reserved by ADR-017 becomes
`SHA256("sdc:reviewed-ark-entitlement:v1\0" || canonical_registry_entry_json)`, using the same
canonical JSON rule and excluding the derived anchor itself; it is neither an arbitrary 64-hex
value nor a digest copied from the bundle manifest. The freezer cannot update the registry, and
entitlement review and authorization approval must be separate commits, with the former an
ancestor of the latter.

The next implementation PR will expose only the following conceptual trust interface; callers do
not receive loose fields that can be recombined:

```text
load_trusted_ark_entitlement(
  reviewed_bundle_id, manifest_path, object_root, at
) -> TrustedArkEntitlement
```

`reviewed_bundle_id` must resolve exactly once in the source-controlled registry before either path
is inspected. The loader verifies the entire closure from the same opened bytes, revalidates the
snapshot/profile and returns an opaque immutable value containing the reviewed registry-entry
digest. Candidate construction accepts only that value, never a caller-supplied anchor and date.

## Runtime-release, queue and ledger identity

The reviewed runtime-release manifest will bind the Git commit, built package digest, dependency
lock digest, Alembic head, dedicated Worker entrypoint, Ark submission-policy digest,
runtime-policy digest, exact Task Queue, ledger ID, deployment ID and account/credential binding
digests. A release digest cannot be supplied through an arbitrary environment variable and call
itself reviewed; it requires a positive Git registry entry.

One exact non-default Task Queue is reviewed for one authorization and must match the release
manifest, authorization, Worker configuration and Temporal Activity metadata. The Worker
registers only `CanaryWorkflow`, its state activity, and dedicated Canary submit/watch/download
activities. It does not register `DramaWorkflow`, generic submit/generate, a legacy authorization
loader or an Attempt-2 route. Activity concurrency and Ark submit concurrency are both one.

The ledger ID and deployment ID are read from an immutable singleton record in the selected
PostgreSQL database. The ledger ID matches the authorization and release manifest; the deployment
ID matches the release registry and is transitively bound by the authorization's release digest.
Neither is accepted from a self-reported environment variable. This prevents accidental use of
another empty database or deployment; it does not defend against a database administrator
deliberately cloning or rewriting the entire ledger. That administrative boundary remains part of
deployment review.

## Atomic claim interface

The implementation will add a dedicated store operation with no legacy fallback. Its conceptual
interfaces are:

```text
claim_evidence_bound_canary(private_binding, frozen_execution, runtime_identity)
  -> NEW_POST_PERMIT | RESUME_OWNED_TASK | HUMAN_GATE
submit_once(new_post_permit, operation_secret)
  -> SUBMITTED_CLAIM_RECEIPT | HUMAN_GATE
record_owned_task(submitted_claim_receipt)
  -> OWNED_TASK | HUMAN_GATE
require_owned_task(private_binding, task_id, operation)
  -> OWNED_TASK | HUMAN_GATE
```

The private binding comes only from the positively registered ADR-017 loader. These methods do not
accept loose hashes, legacy plans, old authorizations or a union fallback.

The method opens one PostgreSQL transaction and performs the following in order:

1. lock the exact Run row and immutable ledger/deployment singleton;
2. after all locks are held, read `clock_timestamp()` once as timezone-aware database time;
3. enforce the exclusive authorization, capability/pricing and entitlement deadlines, including
   an operational guard band for Key loading and the socket write;
4. prove Run, Job, Attempt 1, request fingerprint, authorization, plan, execution, evidence,
   entitlement, release, queue, ledger, region, policy and cost equality;
5. insert the Attempt-1 reservation in `POST_IN_FLIGHT`, insert the complete immutable ADR-017
   authorization-use row with `POST_IN_FLIGHT`, and append the claim event; and
6. commit all three effects together or roll all of them back.

Only the caller whose new inserts commit receives `NEW_POST_PERMIT`. It is a private,
non-serializable, process-local, one-consumption value and cannot be reconstructed from database
rows or Temporal history. A uniqueness conflict, partial mismatch or uncertain transaction result
never receives a permit.

The authorization-use row remains immutable and permanently records that the authorization was
consumed while a POST may have been in flight; it is never updated to `SUBMITTED`. Mutable Provider
progress lives on the Attempt. A concurrent loser or redelivery may classify existing state in a
new read-only transaction, but it may not reinterpret an existing claim as a new-post permit.

If the exact claim already has a durably owned Provider task ID, the method returns
`RESUME_OWNED_TASK` and permits only watch/download. If a claim exists without that task ID, the
result is `SUBMISSION_UNKNOWN -> HUMAN_GATE`; it must not create a new authorization, Attempt,
Run or POST. A conflicting claim also enters `HUMAN_GATE`.

If the transaction commit result itself is unknown, no permit is returned. A separate read-only
classification may discover an owned task and resume it; any committed-or-possibly-committed claim
without ownership is `SUBMISSION_UNKNOWN`. The implementation never assumes rollback after a
lost database connection.

## Secret and socket boundary

The Worker validates every non-secret static and durable gate before asking the secret provider
for the exact reviewed resource version. Secret access is operation-specific: submit requires the
new `NEW_POST_PERMIT`; inspect requires an exact `OWNED_TASK`; download remains credential-free.
The Key is returned only to one short-lived local Provider operation and is not placed in
process-wide environment state, child-process state, Temporal payloads, logs, events, database
rows or exception text. The local reference is released and the client is closed after the
operation. Python cannot promise memory zeroization, so the design does not claim that the Key is
erased immediately after client construction.

The reviewed runtime policy fixes `claim_to_socket_max_ms=10000` and
`expiry_guard_band_ms=30000`; the release manifest records both values and the authorization binds
their runtime-policy digest. Claim requires `db_now + expiry_guard_band_ms` to remain strictly
before every deadline. After Key loading, the owner of `NEW_POST_PERMIT` obtains a new
`clock_timestamp()` and requires both `db_now + claim_to_socket_max_ms` before every deadline and
elapsed monotonic handoff time no greater than `claim_to_socket_max_ms`. It then consumes the
in-memory permit immediately before the fixed Ark `POST`. There is no retry loop. Redirects,
environment proxies, endpoint overrides, 429, 5xx, transport failure, malformed response or a
response without one safely parsed task ID cannot produce another POST.

Claim commit, Key loading, final database check and socket write stay within one non-retrying
submit Activity and a short monotonic handoff deadline. The permit is not placed in a Temporal
payload or carried across an Activity boundary. Expiry, secret unavailability or process failure
after claim consumes the authorization and closes the path; even when no socket write occurred,
replay sees claim/no task and enters `SUBMISSION_UNKNOWN` rather than guessing or replacing it.

- A safe explicit rejection enters `HUMAN_GATE` with bounded diagnostics.
- A transport error, 5xx, malformed response, missing task ID or any uncertain acceptance enters
  `SUBMISSION_UNKNOWN -> HUMAN_GATE`.
- A safely parsed task ID is persisted with claim, Run, Job, Attempt, Provider, model and request
  fingerprint ownership before watch begins.
- Failure to persist that ownership after the socket write is `SUBMISSION_UNKNOWN`; it is never a
  reason to submit again.

## Task ownership and recovery

Watch and download accept a task ID only by loading the owned record for the exact claim. They do
not trust a task ID supplied solely by a Workflow payload, environment value or operator input.
`submit_once` consumes the post capability and returns a different, non-authorizing
`SUBMITTED_CLAIM_RECEIPT` only for one safely parsed task ID; that receipt can persist ownership but
can never issue another POST. Ownership is established by a conditional transaction that requires
the exact authorization, ledger, release and Attempt state, an empty task-ID field and one affected
row. The same transaction writes the task ID, `SUBMITTED`, `submitted_at` and one acceptance event.
An unknown commit result is classified by a later read-only transaction. Replaying the same task ID
is idempotent; a different ID or Provider-level ownership collision enters `HUMAN_GATE`. The task
ID returned by every later Provider observation or artifact reference must equal that owned record.

After ownership is durable, Worker restart may resume non-mutating inspect and idempotent download
for that same ID. Authorization or evidence expiry after accepted submission does not authorize a
new POST, but does not prevent closing and archiving the already owned task.

If the Worker restarts with `POST_IN_FLIGHT` and no owned task ID, it enters `HUMAN_GATE` without
reading the Key. If ownership exists, it may read the reviewed secret only for inspect when the
Provider requires authentication, and may download only the returned result for that owned task.
Temporary output remains unpublished until digest, size and ffprobe checks pass.

Generic observation persistence is not used for this Canary because its historical retry state can
lead to another creative Attempt. A dedicated Canary state path permits only the owned task to move
through `SUBMITTED`, `WATCHING`, `DOWNLOADING` and one terminal state, and never creates Attempt 2.

## Acceptance and implementation boundary

The implementation must prove, with local stubs and real PostgreSQL/Temporal integration tests,
that every possible execution has Attempt <= 1 and Provider POST count <= 1. Every negative test
also asserts the strongest applicable zero-side-effect boundary: zero claim, zero Key read, zero
Provider I/O or zero replacement POST.

Detailed crash windows, test lanes, implementation PR order and operational stop conditions are in
`docs/runbooks/SDC-EVIDENCE-BOUND-LIVE-CANARY.md`.

This ADR is a design approval only. Changing its status or merging its documentation does not
populate an entitlement or authorization registry and does not authorize Key access or Ark.
