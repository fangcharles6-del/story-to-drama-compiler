# SDC-ADR-009: Durable runtime identity and retry ownership

**Status:** Accepted

## Context

Compiled IDs identify deterministic content and therefore repeat for identical `StoryInput`.
They cannot identify an execution. Temporal replay also requires workflow inputs and payload
serialization to remain deterministic, while provider calls require durable limits independent of
Temporal activity redelivery.

## Decision

- Every client submission creates an opaque, unique `run_id`; Temporal `workflow_id` is exactly
  that value. The workflow receives both `run_id` and the immutable `JobGraph`. Compiled graph,
  job, and idempotency IDs remain stable across runs.
- PostgreSQL artifacts, events, provider attempts, queries, updates, primary IDs and idempotency
  conflict targets are scoped by `run_id`. Event uniqueness is `(run_id, idempotency_key)`, attempt
  uniqueness is `(run_id, job_id, attempt)`, and the current-candidate partial unique index is
  `(run_id, job_id) WHERE is_current=true`.
- Client and worker use the same Temporal Pydantic v2 payload converter. Workflow activity retry
  policy sets `maximum_attempts=1`; Temporal never adds a provider attempt.
- The Provider boundary owns a hard two-attempt limit. Both failures yield `STOP-2`, with no hidden
  third call; further progress requires an explicit human decision.
- Schema evolution uses explicit Alembic revisions. Revision 0003 deletes unowned legacy artifact
  rows because their run cannot be inferred, adds artifact run ownership, and replaces all global
  uniqueness constraints and the partial index. Upgrade/downgrade/upgrade and `alembic check` are
  required integration checks.
- Activities receive a session factory, not a shared `AsyncSession`; each transaction obtains its
  own session so concurrent activities never share SQLAlchemy session state.

## Consequences

Two runs of identical input coexist while retaining deterministic compilation. Provider retries
remain auditable through restarts and activity redelivery. Deployments must apply revision 0003
before running the new worker.
