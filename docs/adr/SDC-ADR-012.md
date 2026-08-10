# SDC-ADR-012: Deterministic single-task canary operation

- **Status:** Accepted
- **Date:** 2026-08-10
- **Version:** V01

## Decision

Before any separately approved `SDC-CANARY-001` execution, SDC freezes one exact Temporal
Workflow payload. It contains a caller-selected fixed `run_id`, the deterministic one-Job
`JobGraph`, and the complete `ProviderRequest`. The Workflow ID equals that fixed `run_id`; the
request `run_id`, `job_id`, prompt, duration, Provider parameters, and fingerprint must match the
Workflow payload. Any mismatch fails before Provider submission.

The first canary route is fixed to Volcengine Ark model `doubao-seedance-2-0-260128`, 9:16,
1080p, 4000 ms, text-only input, `generate_audio=false`, creative Attempt 1, one Job, one current
candidate, and no more than one POST. A remote failure, ambiguous result, rejection, or other gate
condition stops at `HUMAN_GATE`; the canary route never enters creative Attempt 2. Normal runtime
two-Attempt and `STOP-2` behavior remains unchanged outside this route.

The reviewed cost ceiling may never exceed CNY 15. Current capability and pricing snapshots can
set a lower ceiling and still fail closed. The zero-network planner freezes the exact execution
payload and emits a `NOT_AUTHORIZED` plan. A separate offline command may turn a separately
approved plan into a one-use `LiveAuthorization`; creating that artifact does not start a Workflow.
Execution is a third, explicit client action and remains impossible without the worker-side
evidence, authorization, secret, and durable one-use gate established by SDC-ADR-011.

## BUILD-005 boundary

BUILD-005 authorizes contracts, explicit Provider parameters, deterministic request/Workflow
binding, single-task preflight, separate preparation/authorization/execution commands, schemas,
documentation, mocks, and zero-network tests. It does not authorize a real Ark call, API Key
injection, service activation, recharge, purchase, paid generation, or production deployment.
Actual execution still requires a separate `SDC-CANARY-001` approval based on official capability
and price evidence captured on the execution date.
