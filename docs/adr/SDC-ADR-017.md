# SDC-ADR-017: Inert evidence-bound authorization and runtime contracts

- **Status:** Accepted
- **Date:** 2026-08-15
- **Version:** V01

## Decision

SDC adds a new `EvidenceBoundLiveAuthorization` contract without reopening the retired
`LiveAuthorization` path. The new object is an inert authorization candidate: its JSON file,
authorization ID, nonce and `max_posts=1` value grant no Provider authority by themselves. The
offline candidate builder re-verifies the Git-reviewed FRESH bundle and its complete CAS closure,
then binds the exact `EvidenceBoundCanaryPlan`, `CanaryExecution`, Ark submission policy, runtime
policy, runtime release, capability and pricing contracts, evidence bundle and logical tree,
`cn-beijing` region, Task Queue, durable ledger, Run, Job, Attempt 1, request fingerprint, cost
limit, validity windows and an independent entitlement-anchor identifier.

Candidate construction prints `mode=candidate-only-not-approved` and the canonical authorization
SHA-256. The CLI generates its nonce internally rather than accepting it through process arguments;
the pure builder accepts an explicit nonce only for deterministic offline tests. A separate
authority must approve that exact digest. Supplying the candidate file itself,
copying its digest into another file, or choosing an authorization ID or nonce is not independent
approval. This delivery provides a separate Git-reviewed positive authorization registry and
validates its entry before reading authorization artifacts. The registry is deliberately empty:
candidate construction never edits it, and no authorization digest is approved by this PR. A
future exact entry requires its own review and commit. No signature service or signing key is
introduced. Consequently, no candidate produced by this delivery is operational.

The runtime binding validator is module-private; supported code constructs it only through the
loader. The loader independently reloads only the new plan, execution and authorization types, re-resolves
the positive FRESH registry entry, verifies the full bundle closure, resolves the exact
authorization digest from the separate positive registry, matches its reviewed fields and runtime
bindings, and rechecks request, cost and expiry constraints. It is deliberately not accepted by
the production Worker or `RuntimeActivities`.

## Wire and runtime-policy binding

The Ark submission-policy digest is domain-separated and covers the fixed provider, region,
official `https://ark.cn-beijing.volces.com/api/v3` base URL, HTTP `POST`,
`/contents/generations/tasks` path, a maximum of one submit call and the exact credential-free JSON
payload derived from the frozen `ProviderRequest`. The Ark adapter uses that same pure payload
builder. Its default HTTP clients disable environment proxy inheritance and redirects. These
changes make future policy drift detectable; they do not permit the adapter to be constructed by
the Worker in this delivery.

The separate runtime-policy digest covers the dedicated Task Queue and ledger identity, frozen
Canary request requirement, Attempt 1, one submit call, Activity concurrency one, and rejection of
legacy plans, legacy authorizations and the generic submit activity. A separately supplied runtime
release digest binds the reviewed implementation identity. Neither digest is a substitute for
review or live approval.

## Persistence declaration

Alembic revision `0007` extends the existing append-only `live_authorization_uses` table with
nullable evidence-bound claim fields. It records the authorization, plan, execution, submission
policy, runtime policy and runtime release digests; bundle/tree and validity; entitlement anchor;
region; Task Queue; ledger; authorization times; nonce digest; and `POST_IN_FLIGHT` claim state.
Partial unique indexes reserve one authorization digest, plan, nonce and evidence-bound
`(run_id, job_id, attempt)` tuple; a completeness check prevents partial evidence-bound rows; and
PostgreSQL triggers reject updates, deletes and truncation.
Historical rows remain valid because the new fields are nullable when no new document type is
present. Downgrade to `0006` is allowed only while no evidence-bound claim exists; otherwise it
fails before dropping triggers, constraints, indexes or columns so that audit bindings cannot be
silently erased.

Revision `0007` is schema preparation only. This delivery does not insert an evidence-bound claim,
does not implement the atomic claim transaction and does not connect the table to Provider I/O.

## Hard execution boundary

Ark Worker startup remains unconditionally disabled before any API Key is read. Legacy guard
loading remains disabled. Direct construction of `RuntimeActivities` with provider
`volcengine_ark` fails closed at every submit, watch, download and legacy-generate entrypoint before
calling the Provider. Submit records `LIVE_NOT_AUTHORIZED`; watch returns that failure class; and
download or legacy generation returns `HUMAN_GATE`. None reserves an Attempt or consumes an
authorization. The retired `LiveSubmissionGuard` also fails at construction. The production
Worker therefore cannot consume either the historical or new authorization contract, regardless
of environment variables or caller-supplied objects.

This delivery must not create a real authorization, read or inject an API Key, start Worker,
Temporal, PostgreSQL or another service, contact Ark, recharge, purchase, claim a trial, or issue a
Provider request. Synthetic in-memory and temporary-file test candidates do not grant authority.

## Entitlement boundary

The current `ark-canary-capability-pricing-v1` FRESH bundle proves only reviewed capability and
pricing. It contains no current entitlement evidence for the exact model and `cn-beijing` account
scope. The new contract reserves an entitlement anchor and expiry, but this delivery does not
define its evidence profile, positive trust registry or verification procedure. An arbitrary
64-hex value is not entitlement proof. The current FRESH bundle and its plan therefore remain
insufficient for live authorization.

## Required future delivery

Any later proposal to open the live path requires a new ADR and explicit approval. At minimum it
must deliver and independently test all of the following as one fail-closed boundary:

- a current, independently reviewed entitlement artifact and positive trust mechanism for the
  exact model, account scope and `cn-beijing` region;
- a separately reviewed, still-current positive-registry entry for the exact authorization
  SHA-256 and all of its bound identities, or a separately approved stronger authority;
- an approved runtime-release identity and a single durable ledger/deployment identity;
- one PostgreSQL transaction that reserves Attempt 1, consumes the approved authorization and
  records `POST_IN_FLIGHT` before any socket write, using database UTC and an exclusive expiry
  boundary;
- replay handling that treats a consumed or `POST_IN_FLIGHT` claim without a persisted task ID as
  `SUBMISSION_UNKNOWN -> HUMAN_GATE` and never submits again;
- a dedicated Worker that reads the Key only after all static and durable gates pass, registers
  only `CanaryWorkflow`, fixes Activity concurrency to one, rejects the generic submit/generate
  routes, and validates task-ID ownership before watch or download; and
- offline and integration tests proving zero legacy fallback, zero Attempt 2, at most one Ark POST,
  no automatic retry after rejection or ambiguity, and append-only claim durability across worker
  restart.

Until that delivery is approved and merged, the only supported Worker remains the FakeProvider
path and every Ark execution attempt must stop at `HUMAN_GATE` with zero POSTs.
