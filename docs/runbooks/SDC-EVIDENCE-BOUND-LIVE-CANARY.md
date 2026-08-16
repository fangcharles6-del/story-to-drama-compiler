# Evidence-bound Live Canary implementation plan (non-operational)

This document is the implementation and verification plan for proposed SDC-ADR-018. It contains
no executable live command. Until every implementation PR is merged and a separate short-lived
activation change is explicitly approved, Ark remains disabled and the only supported Worker uses
FakeProvider.

## Fixed operation

- Provider/model/region: `volcengine_ark` / `doubao-seedance-2-0-260128` / `cn-beijing`.
- One frozen Run, one Job, Attempt 1, one current candidate and at most one Ark POST.
- Text only, 9:16, 1080p, 24 fps, 4000 ms and `generate_audio=false`.
- No fallback model, Provider, region, endpoint, Task Queue, ledger or secret version.
- No recharge, purchase, trial claim or automatic retry.
- Any drift, expiry, rejection, ambiguity or unknown durable state enters `HUMAN_GATE`.

## Required gate order

1. Resolve the positive capability/pricing registry before reading its bundle.
2. Resolve the positive entitlement registry before reading its bundle.
3. Verify both complete CAS closures and their exclusive validity deadlines.
4. Verify the exact plan, execution, request fingerprint, cost and Ark payload-policy digest.
5. Resolve the reviewed runtime release, Task Queue, ledger/deployment and credential binding.
6. Resolve the exact positive authorization entry before reading the authorization candidate.
7. Validate all candidate bindings and output paths without reading a Key.
8. Make the atomic PostgreSQL Attempt-1 plus `POST_IN_FLIGHT` claim using database UTC.
9. Only the new-claim owner loads the exact reviewed secret version.
10. Recheck database time, consume the in-memory permit and issue the only POST.
11. Persist task ownership before any watch or download.

The entitlement observation is independently reviewed and valid for at most four hours, ending
earlier at any source deadline or local capture-day boundary. It binds the exact Seedance model,
`cn-beijing`, task-create operation, pseudonymous account scope and reviewed secret-store resource
version. It does not expose or prove the Key value, balance or quota. The entitlement review commit
must precede the distinct authorization-approval commit.

No step may be reordered or repaired by creating another Run, authorization, Attempt or POST.

## State and recovery table

| Durable observation | Result | Allowed next action |
|---|---|---|
| No claim | Not submitted | Re-run static gates; only a new atomic claim may proceed |
| Transaction outcome unknown | `SUBMISSION_UNKNOWN` | Reconcile database; never assume rollback and never POST |
| `POST_IN_FLIGHT`, no owned task ID | `SUBMISSION_UNKNOWN` | `HUMAN_GATE`; no Key read and no replacement POST |
| Explicit safe rejection recorded | `HUMAN_GATE` | Review bounded diagnostics; no retry |
| Socket/5xx/malformed response ambiguity | `SUBMISSION_UNKNOWN` | Manual Provider reconciliation only |
| Owned task ID, remote queued/running | Existing accepted task | Inspect only that ID |
| Owned task ID, remote succeeded | Existing accepted task | Download and verify only that result |
| Owned task ID, remote failed/expired | `HUMAN_GATE` | Close the one Canary; no Attempt 2 |
| Verified current artifact | `SUCCEEDED` | Freeze audit evidence and stop Worker |

## Test matrix

### Offline and unit tests

- Reject empty, unknown, duplicate, malformed, not-yet-reviewed or expired capability/pricing,
  entitlement, runtime-release and authorization registry entries before artifact reads.
- Reject missing/extra/tampered bundle members, tree drift, wrong profile, non-`FRESH` capture,
  unsafe path, link/junction, invalid UTF-8, duplicate JSON key, non-finite number and digest drift.
- Reject encrypted or oversized entitlement PDFs, attachments, forms, JavaScript, open actions and
  external URI actions; test exact 16-MiB/64-KiB acceptance boundaries and reject bytes beyond
  them.
- Require `capture.source_url == snapshot.source_url`; capture member paths equal the bundle's two
  exact logical paths; the snapshot evidence digest equal both the PDF object hash and registry raw
  evidence digest; bundle creation equal capture/snapshot/registry capture time; and every
  bundle/capture/snapshot/registry deadline equal. Reject each single-field mismatch.
- Bind exact model, account scope, region, credential resource version, plan, execution, request,
  payload policy, runtime policy, release, queue, ledger, cost and all expiry values.
- Reject another operation, similar/unversioned model, account-scope mismatch, `DISABLED` or
  `UNKNOWN` entitlement, future-dated review and the exact exclusive-expiry boundary.
- Reject legacy plans, legacy authorizations, generic submit/generate and Attempt 2.
- Prove zero Key access for every failure before a successful claim.
- After a successful claim, test missing secret, secret-version drift, final database time exactly
  at/after a deadline, exhausted monotonic handoff budget and insufficient guard band. Each leaves
  one consumed claim, zero POSTs and replay-to-`SUBMISSION_UNKNOWN`, with no replacement permit.
- Count secret access by operation: submit may read once only with a new permit, owned inspect may
  read once for that task, and replay without ownership or credential-free download reads zero.
- Prove the default Ark clients disable redirects and environment proxy inheritance and that no
  endpoint/client override is accepted by the production factory.
- Classify 429 and safe 4xx as terminal; classify 5xx, transport, malformed or missing task ID as
  ambiguous. Every case has submit-call count <= 1.

### PostgreSQL integration tests

- Exercise migration upgrade/downgrade, legacy-row preservation, complete-row checks, append-only
  UPDATE/DELETE/TRUNCATE protection and downgrade rejection when a claim exists.
- In one transaction lock the Run, obtain database time, reserve Attempt 1, insert the complete
  `POST_IN_FLIGHT` authorization use and append the claim event.
- Roll back every effect on stale time, drift, uniqueness conflict or statement failure.
- Race two independent connections for the same authorization, plan, nonce and Run/Job/Attempt;
  exactly one may receive a new-post permit.
- Test database time immediately before, exactly at and after each exclusive deadline. Application
  clock skew must not widen the window.
- Test deadlock, timeout, lost connection and unknown commit result. Unknown state never produces a
  permit or a retry.
- Require task ownership to match claim, Run, Job, Attempt, Provider, model and request fingerprint
  before inspect or download.
- Persist the same returned task ID idempotently; reject a different task ID, wrong owner or a
  claim/Attempt partial row without any Provider I/O.

### Temporal and Worker integration tests

- The dedicated queue exposes only `CanaryWorkflow` and dedicated state/submit/watch/download
  activities with Activity concurrency one.
- Submit Activity has `maximum_attempts=1`; timeout, cancellation, duplicate workflow start and
  Worker restart cannot schedule Attempt 2 or a second submit.
- A replay with claim/no task ID enters `HUMAN_GATE`; a replay with ownership resumes only the same
  task ID.
- Watch/download technical retries never call submit and cannot change ownership.
- Duplicate Activity completion cannot duplicate claim, event, artifact or current candidate.
- Startup failure and every pre-claim gate failure occur before secret-provider access.

### Crash-window oracle

Use a local counting transport plus real PostgreSQL and Temporal. Inject process failure at each
boundary:

| Window | Expected durable result | Maximum POST count |
|---|---|---:|
| C0 before static validation | No claim | 0 |
| C1 after validation, before transaction | No claim | 0 |
| C2 inside transaction, before commit | Full rollback | 0 |
| C3 after claim commit, before Key read | Claim/no task ID; `SUBMISSION_UNKNOWN` on replay | 0 |
| C4 after Key read, final DB/monotonic gate fails | Claim/no task ID; `SUBMISSION_UNKNOWN` on replay | 0 |
| C5 socket write or response lost | Ambiguous claim | 1 |
| C6 accepted response, before task ownership commit | Ambiguous claim | 1 |
| C7 ownership commit, before Activity acknowledgement | Resume same task | 1 |
| C8 during watch | Resume same task | 1 |
| C9 during temporary download | Retry same download | 1 |
| C10 artifact commit, before acknowledgement | Reuse verified artifact | 1 |

Every row also asserts Attempt <= 1, no generic route, no secret in logs/history/database/events,
and no replacement authorization.

The real Ark Canary is never used to fill a missing test cell. Only after the local counting
transport, PostgreSQL and Temporal matrix is green may an independently approved activation be
considered.

## Follow-up PR sequence

Each PR must be independently green and must not create a half-open live path.

1. **Entitlement trust (PR1, this delivery)**: add the snapshot/profile/schema, offline freezer,
   verifier and an empty positive registry. Ark remains unreachable.
2. **Atomic ledger (PR2, this delivery)**: add migration `0008`, the private claim interface,
   database-time transaction, replay classification, task ownership and PostgreSQL tests without
   rewriting released revision `0007`. The runtime-identity table and authorization registry stay
   empty; there is no Provider wiring or POST authority.
3. **Dedicated Canary runtime** (1.5-2.5 days): add the dedicated Worker entrypoint, private binding,
   lazy secret provider and owned watch/download using only a local stub. Authorization registry
   remains empty.
4. **Crash and Temporal proof** (2.5-3.5 days): implement C0-C10 injection, concurrency races and
   exact-one-submit end-to-end tests. Merge requires every side-effect count assertion to pass.
5. **Release and evidence trust** (1-1.5 days plus review): freeze the final release, queue, ledger,
   credential binding and execution-day capability/pricing/entitlement evidence. In a distinct
   reviewed commit, add and merge only the exact entitlement registry entry. Add no authorization
   entry; the system remains unable to POST.
6. **Activation data only** (0.5 day plus independent approval): from the already merged
   entitlement-trust commit, generate the inert candidate and submit a later short-lived change
   containing only the exact authorization-registry entry. This is the only POST-authority-changing
   diff and its entitlement commit must already be an ancestor.
7. **Observed execution and archive** (out of scope): requires another explicit operational
   approval and a separate runbook after all code, evidence and activation gates are current. This
   document intentionally provides no Key injection, service startup or Ark execution steps.

The engineering estimate is 13-18 engineer-days including integration and crash-window risk.
Entitlement availability, evidence validity and independent review can add 1-3 calendar days and
cannot be replaced by engineering shortcuts.

## Stop conditions

Stop without cleanup, retry or alternate identity on any registry mismatch, expired evidence,
unknown database outcome, missing task ownership, absent entitlement, secret metadata drift,
queue/ledger/release drift, unexpected poller, unexpected process, Provider ambiguity or nonzero
state before execution. Preserve the database and Temporal state needed for reconciliation.

This plan never authorizes changing configuration in the Provider console, creating or viewing a
Key, buying resources, claiming a trial or using a live Provider response as a test fixture.
