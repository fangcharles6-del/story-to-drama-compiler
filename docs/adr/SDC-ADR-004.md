# SDC-ADR-004: Durable workflow state

- **Status:** Accepted

## Decision

The workflow owns state, events append only, and operations are idempotent.

## Engineering impact

Temporal orchestrates; PostgreSQL records state and uniquely keyed immutable events/artifacts.
