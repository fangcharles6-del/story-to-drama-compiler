# ARK-CANARY-001 runbook (preparation and inert contracts only)

This runbook prepares review evidence and describes fail-closed contracts. BUILD-004 through
ADR-017 do **not** authorize the live step.

## 1. Capture current evidence

An operator must capture the official Seedance 2.0 capability and price rows at execution time.
Record their URLs, page update timestamps, capture timestamps, validity deadlines, and SHA-256 of
the saved evidence. Do not infer a unit or price from a search-result excerpt. The capability
snapshot must retain model `doubao-seedance-2-0-260128`, 9:16, 1080p, 24 fps, and 4–15 seconds.

For the pinned 4000 ms request, SDC's R6-calibrated safety floor reserves one terminal output frame
in addition to the nominal 96 frames. This is a conservative local preflight rule, not a Provider
SLA or a hard billing cap. The calibrated billing floor is therefore
`(ceil(4000 * 24 / 1000) + 1) * 1080 * 1920 / 1024 = 196425` provider tokens. At CNY 51 per
million tokens this is CNY 10.017675. A snapshot that records only 194400 tokens / CNY 9.9144
fails closed because it does not cover the frame-rounded output observed by SDC-CANARY-001 V02-R6.
The live gate applies this arithmetic only when the pricing snapshot uses the reviewed
`provider-token` billing unit; an unknown unit fails before authorization consumption or POST.

Official sources:

- Capability: <https://www.volcengine.com/docs/82379/1330310>
- Pricing: <https://docs.volcengine.com/docs/82379/1544106>
- API task creation: <https://docs.volcengine.com/docs/82379/1520757>

Store evidence outside source control. Never place an API Key, Bearer header, signed input URL, or
signed result URL in a snapshot.

## 2. Freeze reviewed evidence and the deterministic zero-network plan

The historical loose-snapshot `sdc.canary` path is not evidence-bound. For a new execution-day
plan, first follow `SDC-FRESH-EVIDENCE-PLANNING.md`: freeze the two sanitized official PDFs and
matching snapshots, then obtain a separate reviewed registry commit for the resulting bundle ID.

Prepare a one-beat `StoryInput` whose duration is exactly 4000 ms. Select the final `run_id` once;
do not replace it after review. With the reviewed bundle on the current baseline, run:

```bash
uv run python -m sdc.fresh_canary_plan \
  --fresh-evidence-root .artifacts/evidence-current/v1 \
  --reviewed-evidence-bundle-id <FULL_REVIEWED_BUNDLE_ID> \
  --story .artifacts/canary/story.json \
  --run-id <FIXED_RUN_ID> \
  --max-cost-cny <HUMAN_APPROVED_LIMIT_NOT_OVER_15_CNY> \
  --frozen-request-output .artifacts/canary/request-frozen.json \
  --execution-output .artifacts/canary/execution.json \
  --output .artifacts/canary/plan.json
```

Successful output must identify `sdc.evidence-bound-canary-plan`, contain
`"state": "NOT_AUTHORIZED"` and `"posts_allowed": 0`, and bind the reviewed bundle ID/tree/expiry.
This command contains no HTTP client and makes no provider request. The execution artifact must
validate as one Job, Attempt 1, Seedance 2.0, 9:16, 1080p, 4000 ms, text-only, and
`"generate_audio": false`. Its request `run_id`, `job_id`, and fingerprint are the values that the
Workflow must later receive unchanged.

## 3. Human review boundary

Review the frozen request fingerprint, capability checksum, pricing checksum, and worst-case CNY
cost. Historical BUILD-005 authorization generation is retired; this plan cannot create an
operational authorization. ADR-017 adds a separate `EvidenceBoundLiveAuthorization` candidate
contract, but its file remains inert until an independent authority approves its exact canonical
SHA-256. Its binding includes the plan and execution digests, FRESH bundle/tree, snapshot hashes,
cost, expiry, entitlement-anchor identifier, region, Task Queue, ledger, runtime release and fixed
Ark wire-policy digest. The wire policy covers `cn-beijing`, the official base URL, HTTP `POST`,
`/contents/generations/tasks`, the exact credential-free JSON payload and one submit call.

The historical `sdc.canary_authorize` command is retired and fails closed for both old and new plan
types. `sdc.evidence_authorization` can only emit `mode=candidate-only-not-approved`; its output,
authorization ID, nonce, `max_posts=1` and printed digest grant no authority. Runtime loading first
requires an exact entry in the separate Git-reviewed positive authorization registry, before it
reads plan, execution or authorization artifacts. The registry is empty in this PR and candidate
creation cannot update it. Ark Worker startup and the Ark branch inside `RuntimeActivities` remain
unconditionally disabled; only FakeProvider rehearsal is supported. Stop after offline planning.
Do not convert the plan to the old `CanaryPlan`, fall back to loose snapshots, or treat a candidate
as approval.

## 4. Future live prerequisites and execution (not authorized here)

ADR-017 delivers contract validation and database schema preparation, not the runtime connection.
Proposed ADR-018 specifies the missing entitlement, atomic-claim, replay, dedicated-Worker and
task-ownership boundary, but does not implement or authorize it. Its non-operational verification
plan is `SDC-EVIDENCE-BOUND-LIVE-CANARY.md`.
There is no supported Ark Worker environment-variable set or client action in this version. Legacy
capability, pricing and authorization path variables remain rejected. Do not inject an API Key,
start Worker/Temporal/PostgreSQL, or invoke the Canary client against Ark.

The current `ark-canary-capability-pricing-v1` FRESH bundle contains no entitlement evidence. The
candidate contract reserves `entitlement_anchor_sha256` and `entitlement_valid_until`, but this
version has no entitlement evidence profile, positive registry or verifier. A caller-supplied hash
and date cannot establish current access to `doubao-seedance-2-0-260128` in `cn-beijing`.

A future implementation under ADR-018 must be split into independently green, fail-closed changes
and separately approved before it can atomically deliver:

- current, independently reviewed entitlement for the exact account scope, model and region;
- a separately reviewed, current positive-registry entry for the exact authorization SHA and all
  of its bound identities, not the candidate file or digest copied beside it;
- a reviewed runtime-release digest and one durable ledger/deployment identity;
- a database transaction that reserves Attempt 1, consumes that authorization and persists
  `POST_IN_FLIGHT` before any socket write, using database UTC and an exclusive expiry boundary;
- replay behavior that maps a consumed or in-flight claim without a persisted task ID to
  `SUBMISSION_UNKNOWN -> HUMAN_GATE`, with no replacement POST;
- a dedicated Worker that reads the Key only after every static and durable gate passes, registers
  only `CanaryWorkflow`, fixes Activity concurrency to one, rejects generic submit/generate, and
  verifies task-ID ownership before watch/download; and
- tests proving at most one Ark POST, no creative Attempt 2, no legacy fallback, and no automatic
  resubmission after an explicit rejection, crash or ambiguous outcome.

Non-mutating watch/download technical retries may operate only on a durably owned task ID after a
future accepted submission. They never authorize another creative Attempt or POST.

## 5. Diagnose a rejected or failed request without expanding the evidence surface

Migration `0006` defines the bounded provider-failure diagnostics. ADR-017 adds migration `0007`,
which only declares nullable evidence-bound claim metadata, completeness/uniqueness constraints and
a database append-only trigger. No current code inserts such a claim, and applying `0007` does not
make Ark execution available.

After a future separately approved live delivery, an explicit Ark submission rejection may be
diagnosed using only the bounded columns on the matching `generation_attempts` row:

```sql
SELECT run_id, job_id, attempt, failure_class,
       provider_http_status, provider_error_code,
       provider_request_id_hmac_sha256, provider_error_message
FROM generation_attempts
WHERE run_id = '<FIXED_RUN_ID>' AND job_id = '<FIXED_JOB_ID>' AND attempt = 1;
```

`provider_error_code` is retained only when it exactly matches the reviewed Ark allowlist.
`provider_request_id_hmac_sha256` is a keyed, domain-separated HMAC used only for correlation; the
raw response-header value is never stored.
`provider_error_message` is a local fixed description, not the Ark response message. This
submission-diagnostic path never persists a raw response body, response headers, request payload,
Prompt, API Key, Bearer value, signed input URL, or signed result URL. Run events retain only the
failure classification; the attempt row is the authoritative diagnostic record.

The four diagnostic columns are nullable. `NULL` means the value was unavailable or was not safely
captured; do not infer or backfill it. In particular, migration `0006` cannot recover diagnostics
for a rejection recorded by an earlier version. An explicit rejection still enters `HUMAN_GATE`,
and `SUBMISSION_UNKNOWN` still requires manual reconciliation. Neither condition authorizes a
retry, a replacement authorization, a new Run, a recharge, or a purchase.
