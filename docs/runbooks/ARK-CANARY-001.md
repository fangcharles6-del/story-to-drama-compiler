# ARK-CANARY-001 runbook (preparation only)

This runbook prepares review evidence. BUILD-004 and BUILD-005 do **not** authorize the live step.

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
operational authorization. Any future live delivery and approval must name the exact request and
checksum values, establish an expiry and a cost ceiling no greater than CNY 15, and authorize no
more than one POST for creative Attempt 1.

The historical `sdc.canary_authorize` command is retired and fails closed for both old and new plan
types. Ark Worker startup is also retired; only FakeProvider rehearsal remains available. Stop
after offline planning. Connecting this plan to a new authorization/runtime contract requires a
separate delivery and explicit approval; do not convert it to the old `CanaryPlan` or fall back to
loose snapshot files.

## 4. Future live prerequisites and execution (not authorized here)

The evidence-bound runtime connection is not delivered by ADR-016, so this section remains
historical and is not an execution instruction for a new plan. Only after a future dedicated
delivery and SDC-CANARY-001 approval may an operator inject the Key through a deployment Secret Store
and supply these paths to an isolated worker:

- `SDC_PROVIDER_CAPABILITY_PATH`
- `SDC_PROVIDER_PRICING_PATH`
- `SDC_LIVE_AUTHORIZATION_PATH`

The separately approved client action is:

```bash
uv run python -m sdc.client --canary-execution .artifacts/canary/execution.json
```

The client uses the frozen `run_id` as `workflow_id` and passes the frozen request to the Workflow.
The worker independently reconstructs the request from its explicit Provider profile and fails
closed on any mismatch. The Canary Workflow cannot dispatch Attempt 2.

If any file is missing, mismatched, expired, already consumed, or over budget, the worker/runtime
fails closed before POST. A submission with an unknown outcome enters `HUMAN_GATE`; do not create a
replacement authorization until the remote task state has been manually reconciled.

## 5. Diagnose a rejected or failed request without expanding the evidence surface

Run database migration `0006` before starting a Worker that contains provider-failure diagnostics.
For a future explicit Ark submission rejection, inspect only the bounded columns on the matching
`generation_attempts` row:

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
