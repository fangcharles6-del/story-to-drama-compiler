# ARK-CANARY-001 runbook (preparation only)

This runbook prepares review evidence. BUILD-004 and BUILD-005 do **not** authorize the live step.

## 1. Capture current evidence

An operator must capture the official Seedance 2.0 capability and price rows at execution time.
Record their URLs, page update timestamps, capture timestamps, validity deadlines, and SHA-256 of
the saved evidence. Do not infer a unit or price from a search-result excerpt. The capability
snapshot must retain model `doubao-seedance-2-0-260128`, 9:16, 1080p, 24 fps, and 4–15 seconds.

Official sources:

- Capability: <https://www.volcengine.com/docs/82379/1330310>
- Pricing: <https://docs.volcengine.com/docs/82379/1544106>
- API task creation: <https://docs.volcengine.com/docs/82379/1520757>

Store evidence outside source control. Never place an API Key, Bearer header, signed input URL, or
signed result URL in a snapshot.

## 2. Freeze the deterministic one-task execution and zero-network plan

Prepare current `ProviderCapabilitySnapshot` and `ProviderPricingSnapshot` JSON files plus a
one-beat `StoryInput` whose duration is exactly 4000 ms. Select the final `run_id` once; do not
replace it after review. Then run:

```bash
uv run python -m sdc.canary \
  --capability .artifacts/canary/capability.json \
  --pricing .artifacts/canary/pricing.json \
  --story .artifacts/canary/story.json \
  --run-id <FIXED_RUN_ID> \
  --max-cost-cny <HUMAN_APPROVED_LIMIT_NOT_OVER_15_CNY> \
  --frozen-request-output .artifacts/canary/request-frozen.json \
  --execution-output .artifacts/canary/execution.json \
  --output .artifacts/canary/plan.json
```

Successful output must contain `"state": "NOT_AUTHORIZED"` and `"posts_allowed": 0`. This command
contains no HTTP client and makes no provider request. The execution artifact must validate as one
Job, Attempt 1, Seedance 2.0, 9:16, 1080p, 4000 ms, text-only, and
`"generate_audio": false`. Its request `run_id`, `job_id`, and fingerprint are the values that the
Workflow must later receive unchanged.

## 3. Human review boundary

Review the frozen request fingerprint, capability checksum, pricing checksum, and worst-case CNY
cost. BUILD-005 tests authorization generation but does not authorize creating an operational
authorization. A future SDC-CANARY-001 approval must name the exact request and checksum values,
establish an expiry and a cost ceiling no greater than CNY 15, and authorize no more than one POST
for creative Attempt 1.

After that separate approval, generate (but do not execute) the authorization artifact in its own
step:

```bash
uv run python -m sdc.canary_authorize \
  --plan .artifacts/canary/plan.json \
  --execution .artifacts/canary/execution.json \
  --authorization-id SDC-CANARY-001 \
  --max-cost-cny <APPROVED_LIMIT_NOT_OVER_15_CNY> \
  --expires-at <APPROVED_TIMEZONE_AWARE_EXPIRY> \
  --nonce <APPROVED_64_HEX_NONCE> \
  --output .artifacts/canary/authorization.json
```

This command writes JSON only. It does not start Temporal, load an API Key, or call Ark.

## 4. Future live prerequisites and execution (not authorized here)

Only after SDC-CANARY-001 approval may an operator inject the Key through a deployment Secret Store
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
For a future explicit Ark rejection or remotely failed task, inspect only the bounded columns on
the matching `generation_attempts` row:

```sql
SELECT run_id, job_id, attempt, failure_class,
       provider_http_status, provider_error_code,
       provider_request_id, provider_error_message
FROM generation_attempts
WHERE run_id = '<FIXED_RUN_ID>' AND job_id = '<FIXED_JOB_ID>' AND attempt = 1;
```

`provider_error_code` and `provider_request_id` are restricted opaque identifiers.
`provider_error_message` is a local fixed description, not the Ark response message. The adapter
never persists a raw response body, response headers, request payload, Prompt, API Key, Bearer
value, signed input URL, or signed result URL. Run events retain only the failure classification;
the attempt row is the authoritative diagnostic record.

The four diagnostic columns are nullable. `NULL` means the value was unavailable or was not safely
captured; do not infer or backfill it. In particular, migration `0006` cannot recover diagnostics
for a rejection recorded by an earlier version. An explicit rejection still enters `HUMAN_GATE`,
and `SUBMISSION_UNKNOWN` still requires manual reconciliation. Neither condition authorizes a
retry, a replacement authorization, a new Run, a recharge, or a purchase.
