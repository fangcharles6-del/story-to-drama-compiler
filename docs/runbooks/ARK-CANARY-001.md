# ARK-CANARY-001 runbook (preparation only)

This runbook prepares review evidence. BUILD-004 does **not** authorize the live step.

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

## 2. Create the zero-network plan

Prepare three local JSON files that validate against `ProviderCapabilitySnapshot`,
`ProviderPricingSnapshot`, and `ProviderRequest`. The request may initially use 64 zeroes as its
fingerprint. Then run:

```bash
uv run python -m sdc.canary \
  --capability .artifacts/canary/capability.json \
  --pricing .artifacts/canary/pricing.json \
  --request .artifacts/canary/request-draft.json \
  --max-cost-cny <HUMAN_APPROVED_LIMIT> \
  --frozen-request-output .artifacts/canary/request-frozen.json \
  --output .artifacts/canary/plan.json
```

Successful output must contain `"state": "NOT_AUTHORIZED"` and `"posts_allowed": 0`. This command
contains no HTTP client and makes no provider request.

## 3. Human review boundary

Review the frozen request fingerprint, capability checksum, pricing checksum, and worst-case CNY
cost. Do not create `LiveAuthorization` during BUILD-004. A future SDC-CANARY-001 approval must name
the exact request and checksum values, establish an expiry and cost ceiling, and authorize no more
than one POST for creative Attempt 1.

## 4. Future live prerequisites (not authorized here)

Only after SDC-CANARY-001 approval may an operator inject the Key through a deployment Secret Store
and supply these paths to an isolated worker:

- `SDC_PROVIDER_CAPABILITY_PATH`
- `SDC_PROVIDER_PRICING_PATH`
- `SDC_LIVE_AUTHORIZATION_PATH`

If any file is missing, mismatched, expired, already consumed, or over budget, the worker/runtime
fails closed before POST. A submission with an unknown outcome enters `HUMAN_GATE`; do not create a
replacement authorization until the remote task state has been manually reconciled.
