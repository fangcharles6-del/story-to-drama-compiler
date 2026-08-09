# SDC-ADR-001: Deterministic compiler

- **Status:** Accepted

## Decision

SDC is a deterministic Story-to-Drama Compiler rather than a per-block manual process.

## Engineering impact

Compiler stages are pure, stable, and independently serialized.
