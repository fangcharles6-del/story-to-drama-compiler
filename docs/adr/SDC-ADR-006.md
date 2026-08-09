# SDC-ADR-006: Runtime boundaries

- **Status:** Accepted

## Decision

Generation goes through Provider Gateway and media work through Media Engine; Codex is not runtime control.

## Engineering impact

Adapters remain replaceable; FakeProvider and FFmpeg provide offline verification.
