# SDC-ADR-005: Candidate and attempt limits

- **Status:** Accepted

## Decision

Each job has one current candidate and creative generation has at most two attempts.

## Engineering impact

A second failure enters STOP-2 and requires a human gate; no automatic third attempt exists.
