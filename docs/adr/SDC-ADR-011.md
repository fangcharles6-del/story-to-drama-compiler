# SDC-ADR-011: Versioned provider evidence and live-canary authorization

- **Status:** Accepted
- **Date:** 2026-08-10

## Decision

SDC keeps the accepted Volcengine Ark model `doubao-seedance-2-0-260128`, 9:16 aspect ratio,
1080p resolution, and 4–15 second output boundary. SDC-ADR-010 is not superseded. Seedance 2.0
Fast, Mini, Seedance 2.5, browser automation, provider fallback, and model fallback remain outside
the first live route.

Every live POST must be bound to immutable `ProviderCapabilitySnapshot`,
`ProviderPricingSnapshot`, and `LiveAuthorization` contracts. The snapshots preserve official
source timestamps, expiry, and evidence SHA-256. Authorization binds the exact Provider request
fingerprint, both snapshot checksums, a CNY cost ceiling, an expiry, a nonce, and exactly one POST.
Any missing, stale, revoked, mismatched, or over-budget evidence fails before the provider boundary.

Authorization consumption is persisted before POST and is globally unique. If a worker stops after
consumption, the authorization cannot be replayed; the run requires human review and a separately
approved replacement authorization. This fail-closed ambiguity is preferable to an untracked paid
request. A technical retry of watch or download still addresses the persisted task ID and does not
consume another creative Attempt.

The zero-network canary planner freezes the request and produces a `CanaryPlan` whose state is
`NOT_AUTHORIZED` and whose `posts_allowed` value is zero. A plan is evidence for review, never an
authorization. Real execution requires a separate SDC-CANARY decision and a matching one-use
authorization artifact.

## BUILD-004 boundary

BUILD-004 authorizes contracts, schemas, durable authorization consumption, fail-closed runtime
gates, dry-run tooling, documentation, mocks, and CI. It does not authorize a real Ark API call,
credential injection, service activation, recharge, resource purchase, paid generation, or
production deployment. `FakeProvider` remains the default, maximum two creative Attempts and
STOP-2 remain unchanged, and `SUBMISSION_UNKNOWN` still transitions to `HUMAN_GATE` without an
automatic second POST.
