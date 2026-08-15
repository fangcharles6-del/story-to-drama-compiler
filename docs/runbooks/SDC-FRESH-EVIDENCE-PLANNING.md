# Execution-day FRESH evidence and offline Canary planning

This runbook creates a candidate evidence bundle and, only after a separate reviewed registry
commit, a zero-authority Canary plan. ADR-017 additionally defines an inert evidence-bound
authorization candidate, but does not make it an operational authorization and does not connect it
to Ark. This runbook never acquires evidence itself and never authorizes Ark.

## Hard boundary

- Do not use R2-R6, `.artifacts/evidence-cas/v1`, or any `v02-r6-live` file as FRESH input.
- Do not provide an API Key, credential, authorization, request/response, generated media, account
  page, balance, bill, task ID, HAR, cookie, Worker state, Temporal history or database export.
- Inputs must be newly captured, pre-sanitized official capability and pricing PDFs plus their
  matching `ProviderCapabilitySnapshot` and `ProviderPricingSnapshot` JSON.
- Inputs and outputs must use a local, operator-controlled filesystem with no links, junctions,
  mapped network drive, cloud-sync writer, or concurrent process changing their parent paths.
- No command in Sections 1-3 accesses the network, starts a service, creates an approved or
  operational authorization, or permits a POST. Stop on any mismatch or ambiguous result.

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
available. ADR-017 does not change these boundaries.

## 4. ADR-017 candidate contract is not a live next step

ADR-017 adds `EvidenceBoundLiveAuthorization` and the offline
`sdc.evidence_authorization` candidate builder. A candidate binds the exact plan and execution,
FRESH bundle/tree and snapshot hashes, cost and expiry, `cn-beijing`, Task Queue and ledger, plus
the reviewed Ark wire-policy digest. The wire digest covers the official base URL, HTTP `POST`,
`/contents/generations/tasks`, a maximum of one submit call and the exact credential-free JSON body.
The command prints `mode=candidate-only-not-approved` and a canonical authorization SHA-256.

That output remains inert. The candidate file, its ID, nonce, `max_posts=1`, printed digest, and an
arbitrary caller-supplied approval digest do not establish independent authority. Runtime loading
requires an exact entry in the separate Git-reviewed positive authorization registry. That
registry is empty in this PR, and candidate creation never edits it. The production Worker and
`RuntimeActivities` reject Ark unconditionally and do not accept the new guard. Alembic revision
`0007` only declares the future append-only claim fields; no evidence-bound claim or Provider
operation writes them in this delivery.

Do not run the candidate builder for the current FRESH bundle as if it completed live preparation.
The `ark-canary-capability-pricing-v1` profile contains capability and pricing only. It does not
contain a reviewed entitlement artifact for the exact model, account scope and `cn-beijing`
region. ADR-017 reserves an entitlement-anchor field but does not define or verify its trust
source; an arbitrary 64-hex value is not entitlement evidence.

A future live-enablement delivery requires a current positively trusted entitlement artifact, an
independent authority for the exact authorization SHA, an approved runtime release and durable
ledger, an atomic database `POST_IN_FLIGHT` claim, replay-to-`SUBMISSION_UNKNOWN` handling, and a
dedicated one-concurrency Canary Worker. Proposed SDC-ADR-018 defines that future boundary and its
test/PR sequence in `SDC-EVIDENCE-BOUND-LIVE-CANARY.md`; it is design-only and still requires
explicit implementation and activation approvals. Until then, do not read or inject a Key, start
services, invoke the Canary client against Ark, or create a real authorization.

## Stop conditions

Stop at `HUMAN_GATE` on an unknown or duplicate registry ID, expiry, not-yet-reviewed time, manifest
or CAS drift, extra/missing member, non-FRESH capture, snapshot/provenance mismatch, cost failure,
existing output, missing entitlement trust, missing independent authorization authority, or any
unclear result. Do not repair, extend expiry, relabel legacy evidence, create an alternate registry
file, invent an entitlement anchor, or fall back to loose capability/pricing JSON.
