# Execution-day FRESH evidence and offline Canary planning

This runbook creates a candidate evidence bundle and, only after a separate reviewed registry
commit, a zero-authority Canary plan. It never acquires evidence itself and never authorizes Ark.

## Hard boundary

- Do not use R2-R6, `.artifacts/evidence-cas/v1`, or any `v02-r6-live` file as FRESH input.
- Do not provide an API Key, credential, authorization, request/response, generated media, account
  page, balance, bill, task ID, HAR, cookie, Worker state, Temporal history or database export.
- Inputs must be newly captured, pre-sanitized official capability and pricing PDFs plus their
  matching `ProviderCapabilitySnapshot` and `ProviderPricingSnapshot` JSON.
- Inputs and outputs must use a local, operator-controlled filesystem with no links, junctions,
  mapped network drive, cloud-sync writer, or concurrent process changing their parent paths.
- No command below accesses the network, starts a service, creates `LiveAuthorization`, or permits
  a POST. Stop on any mismatch or ambiguous result.

## 1. Freeze a candidate

Use a fresh namespace separate from the canonical legacy store:

```powershell
uv run python -m sdc.fresh_evidence `
  --capability-snapshot <capability-snapshot.json> `
  --capability-evidence <capability-evidence.pdf> `
  --pricing-snapshot <pricing-snapshot.json> `
  --pricing-evidence <pricing-evidence.pdf> `
  --output-root .artifacts/evidence-current/v1
```

The command prints `mode=candidate-only-not-trusted`, the candidate bundle ID, logical-tree and two
snapshot contract hashes, manifest path, object root, and original expiry. It fixes four logical
members and two FRESH captures, checks the PDF magic bytes and snapshot provenance, then publishes
objects before the manifest. Repeating the same input reuses identical objects; it never replaces
a mismatch.

The bundle remains unusable by the planner at this point.

## 2. Independently review and anchor

Review the sanitized evidence, source URLs and update markers, timestamps, exact Ark model,
capability, price, frame-calibrated cost, logical tree and both snapshot contract hashes. In a
separate reviewed commit, add exactly one `ReviewedFreshEvidence` entry to
`src/sdc/fresh_evidence_registry.py`.

Never copy the ID from the manifest and call that independent review. Never add an expired bundle,
a legacy R2-R6 ID, or an ID whose source evidence was not reviewed. The registry commit is the
positive trust anchor; the CAS is only storage.

## 3. Build a zero-authority plan

After the registry commit is on the reviewed baseline:

```powershell
uv run python -m sdc.fresh_canary_plan `
  --fresh-evidence-root .artifacts/evidence-current/v1 `
  --reviewed-evidence-bundle-id <full-reviewed-64-hex-id> `
  --request <frozen-request.json> `
  --max-cost-cny <reviewed-ceiling> `
  --output <new-evidence-bound-plan.json>
```

The story form uses `--story`, `--run-id`, and `--execution-output` as the historical preparation
flow does. Output files must be new. The planner records one UTC `planned_at`, verifies every CAS
object, checks FRESH validity and the exact profile, parses snapshots from those verified bytes,
and applies the existing request/capability/pricing/cost rules. After validating all output paths,
it checks current UTC time again immediately before producing output; evidence that expired during
planning fails closed.

Expected plan fields include:

- `document_type = sdc.evidence-bound-canary-plan`
- the reviewed `evidence_bundle_id` and logical-tree digest
- `state = NOT_AUTHORIZED`
- `attempt = 1`
- `posts_allowed = 0`

The historical `sdc.canary_authorize` command is retired and fails closed for both legacy and new
plans. The supported Ark Worker startup path is also retired; FakeProvider rehearsal remains
available. Authorization/runtime integration requires a later approved delivery.

## Stop conditions

Stop at `HUMAN_GATE` on an unknown or duplicate registry ID, expiry, not-yet-reviewed time, manifest
or CAS drift, extra/missing member, non-FRESH capture, snapshot/provenance mismatch, cost failure,
existing output, or any unclear result. Do not repair, extend expiry, relabel legacy evidence, create
an alternate registry file, or fall back to loose capability/pricing JSON.
