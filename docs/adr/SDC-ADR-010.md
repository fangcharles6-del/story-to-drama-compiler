# SDC-ADR-010: Durable real-provider execution

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

The first real video provider is the official Volcengine Ark Seedance 2.0 API, pinned to model
`doubao-seedance-2-0-260128`. Execution has three recoverable boundaries: `submit`, `watch`
(`inspect`), and `download`. The remote `provider_task_id` is persisted immediately after submit,
and subsequent work addresses that task rather than issuing another POST.

Technical retries (watch and idempotent download) are separate from creative Attempts. A submit
whose outcome cannot be established is recorded as `SUBMISSION_UNKNOWN` and transitions to
`HUMAN_GATE`; it must never be automatically POSTed again. Explicit remote failure or expiry may
consume the second and final creative Attempt. There is one current candidate per run/job; failure
of Attempt 2 enters `STOP-2`, blocks dependent jobs, and can never create Attempt 3.

Provider-specific commands remain inside adapters and do not enter NIR or PIR. The selected
`ProviderProfile` is frozen for a run and auditable. Production Ark profiles are 9:16, 1080p,
4–15 seconds, initially limited to two in-flight tasks. Unsupported duration fails before POST.
Ark credentials are runtime-only, and signed input/result URLs are never event data.

We reject browser automation of Jimeng, automatic model/provider fallback, and automatic input
splitting or truncation. In particular, the implementation does not switch to Seedance 2.5.

## Operational boundary

This phase authorizes offline implementation, mocks, documentation, and CI only. Real paid calls,
live canaries, credentials, charging, and resource purchases are not authorized. `FakeProvider`
remains the default. Production activation requires a human to enable Ark, inject a secret, define
a cost ceiling, and separately authorize a live canary.
