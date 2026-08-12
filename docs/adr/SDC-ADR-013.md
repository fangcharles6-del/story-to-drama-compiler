# SDC-ADR-013: First canary local infrastructure and rehearsal boundary

- **Status:** Accepted
- **Date:** 2026-08-11
- **Version:** V01

## Decision

The first `SDC-CANARY-001` execution is fixed to a local Windows 10 Pro workstation running
Docker Desktop with the WSL2 Linux-container backend. PostgreSQL 16 and Temporal 1.27 run in local
containers. The SDC Worker and Canary Client run on the Windows host through `uv`; they are not
containerized for this first operation.

PostgreSQL port 5432 and Temporal port 7233 bind only to `127.0.0.1`. No component introduced by
this decision may add a wildcard, LAN, or public listener. The operation uses the dedicated Task
Queue `sdc-canary-001-v01-rehearsal` for the FakeProvider rehearsal and an equally isolated Canary
queue for any later approved real execution. The Worker setting `SDC_ARK_MAX_IN_FLIGHT` is fixed to
`1`, and the Worker Activity maximum concurrency is also one.

Before any real Provider execution, operators must complete a single-Run, single-Job,
single-candidate, Attempt-1-only end-to-end rehearsal with `FakeProvider`. It is fixed to text-only
input, 9:16, 1080p, 24 fps, 4000 ms, and `generate_audio=false`. The rehearsal neither imports the
Ark network adapter nor creates or consumes a `LiveAuthorization`; its Provider HTTP POST count is
zero. A Worker restart, Activity failure, ambiguous condition, or any other abnormal path enters
`HUMAN_GATE` without creating Attempt 2.

The first real Canary must not run in GitHub Actions or on a production VPS. It remains a separate,
explicitly monitored local action after the rehearsal and all execution-day gates pass. Capability
and pricing evidence is time-bounded: expired evidence must not be extended, rolled forward, or
reused. Current official evidence must be captured and frozen again immediately before any real
execution.

## Consequences

The local Compose stack is reachable only from the host loopback interface. The normal
`DramaWorkflow`, its two-Attempt/`STOP-2` behavior, the pinned Seedance model, cost ceilings, and
BUILD-005 production Canary behavior are unchanged. This decision adds no credential, spend,
service activation, live authorization, or permission to contact Volcengine Ark.
