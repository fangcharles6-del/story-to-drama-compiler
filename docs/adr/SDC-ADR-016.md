# SDC-ADR-016: Reviewed FRESH evidence for zero-authority Canary planning

- **Status:** Accepted
- **Date:** 2026-08-15
- **Version:** V01

## Decision

Execution-day capability and pricing evidence may be frozen into a dedicated, immutable
`EvidenceBundle` profile and reused only inside its original validity window. The profile contains
exactly four distinct objects: one sanitized official capability PDF, one capability snapshot JSON,
one sanitized official pricing PDF, and one pricing snapshot JSON. Its two captures are fixed by
the implementation, use acquisition `FRESH`, have no origin or predecessor, and bind each snapshot
to its evidence object, official URL, update time, capture time, and expiry.

Freezing is an offline admission step, not evidence acquisition and not a trust decision. The
freezer accepts four explicit regular files, never scans a directory, rejects legacy Canary and
sealed legacy-CAS paths, parses snapshot JSON with duplicate-key and non-finite-number rejection,
normalizes snapshot timestamps to UTC, and publishes content-addressed objects before a no-replace
manifest. A returned bundle ID is labelled `candidate-only-not-trusted`.

Planner trust is a positive Git-reviewed registry in `sdc.fresh_evidence_registry`. The registry
starts empty. A candidate becomes selectable only after a separate review commits its exact bundle
ID, logical-tree digest, capability and pricing contract digests, validity boundary, and review
time. The planner never derives trust from a manifest, filename, directory, catalog, predecessor,
or arbitrary registry file. Unknown IDs and the five historical R2-R6 bundle IDs are rejected
before a manifest or CAS object is read.

For a reviewed ID, the planner performs this order exactly:

1. resolve the positive registry entry;
2. bind and parse the manifest using that externally reviewed ID;
3. verify every object in the bundle CAS in one read;
4. assert that the complete bundle is current and all captures are `FRESH`;
5. enforce the exact four-member/two-capture Canary profile;
6. parse capability and pricing only from the bytes returned by that verification;
7. cross-check evidence hashes, URL and timestamps against each capture and registry entry; and
8. run the existing provider, request, capability, price and calibrated cost checks at the same
   timezone-aware `planned_at`.

The resulting `EvidenceBoundCanaryPlan` is a new contract, not a subtype of the historical
`CanaryPlan`. It records the bundle ID, logical-tree digest and evidence expiry while remaining
`NOT_AUTHORIZED`, Attempt 1, and `posts_allowed=0`. The structural boundary is inclusive at the
recorded `planned_at`, but the planner rechecks current time after verification and output preflight;
any completion later than `valid_until` is rejected. Operational guidance should retain time for
review rather than depend on the boundary instant.

## Authorization boundary

This decision stops at zero-network planning. It does not change the `LiveAuthorization` contract,
runtime persistence, database schema, or Provider adapter implementation. It retires the
loose-snapshot planner CLI, all supported authorization-generation entry points, and Ark Worker
startup: both the historical `CanaryPlan` path and the new evidence-bound plan fail closed.
FakeProvider rehearsal is unchanged. Connecting a reviewed bundle and its plan to a future
evidence-bound authorization/runtime contract is a separate delivery and approval.

Freezing, reviewing, loading, or planning does not read an API Key or environment secret, create
an authorization or nonce, start Worker, Temporal, PostgreSQL or any service, contact Ark, issue a
Provider request, recharge, purchase, claim a trial, or permit paid generation. The canonical
R2-R6 legacy CAS remains sealed and permanently historical. Direct legacy/archive paths are
rejected mechanically; a copied byte outside those paths is not automatically classified, so the
independent registry review must reject any candidate derived from historical evidence.

## Consequences and acceptance criteria

- Identical semantic snapshots with equivalent timezone offsets produce the same canonical bundle
  bytes and ID; same objects and manifest are reusable without replacement.
- A candidate cannot plan until its full identity and contract hashes receive a separate reviewed
  registry commit.
- Any missing, extra, repeated, relabelled, stale, inherited, legacy, wrong-MIME, wrong-schema,
  wrong-provenance, wrong-digest or mutated member fails closed.
- Bundle verification always covers the complete closure, even though the planner consumes only
  the two snapshot members after verification.
- Strict JSON parsing rejects invalid UTF-8, nested duplicate keys, NaN and oversized snapshots.
- Tests prove zero network and zero authorization side effects and retain the fixed R2-R6 IDs,
  existing contract hashes, old schemas, and request-fingerprint behavior unchanged.
- The integrity wrapper does not prove the truth or sanitization of caller-supplied evidence. The
  independent registry review remains responsible for acquisition provenance, privacy and policy.
