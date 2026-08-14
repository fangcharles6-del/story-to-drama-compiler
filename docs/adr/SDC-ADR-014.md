# SDC-ADR-014: Immutable content-addressed evidence bundles

- **Status:** Accepted
- **Date:** 2026-08-14
- **Version:** V01

## Decision

SDC stores reusable evidence as an immutable `EvidenceBundle` whose identity is a
domain-separated SHA-256 digest of canonical bundle content. Evidence bytes live in a read-only
content-addressed store keyed by their raw SHA-256 digest. A bundle maps canonical POSIX logical
paths to those objects, records capture provenance and original validity windows, and binds the
resolved logical tree with a second domain-separated digest.

The trusted read path requires the caller to supply an expected bundle ID from an independently
anchored round index or review record. A manifest that only validates its own hashes is
self-consistent but not authenticated. Resolution rejects path traversal, Windows device names and
alternate data streams, case-insensitive collisions, links or junctions, undeclared objects, and
any byte-count or digest mismatch. The reader returns bytes verified on the same read rather than a
filesystem path whose contents could be replaced after verification. Freshness checks require an
explicit timezone-aware observation time.

The generated JSON Schema is a portable structural description, not a security verifier. Several
computed and platform-specific invariants—including Windows-safe paths, source-host policy,
sorting and closure, trusted bundle identity, and digest verification—are enforced by the Python
contract and reader. A trusted consumer must use the anchored manifest loader, verify the CAS
bytes, and call the explicit freshness check; schema-only validation or byte verification alone is
insufficient for a live policy decision.

The v1 reader caps a manifest at 4 MiB, each evidence object at 64 MiB, and the deduplicated object
closure at 512 MiB. It stops reading an object as soon as the declared size is exceeded. Evidence
outside those bounds requires a future schema/version decision rather than silently weakening the
reader's memory-safety assumptions.

Evidence acquisition and offline bundle verification remain separate phases. Importing or
inheriting evidence must preserve its original capture and expiry times; a bundle's validity ends
at the earliest capture expiry and can never extend an existing source. This first reader accepts
only `FRESH` captures for construction and freshness decisions. `INHERITED` and `LEGACY_IMPORT`
records remain structurally parseable for the future verified-origin importer, but fail closed if
a caller asks whether they are current. Expired bundles remain valid historical records but cannot
satisfy a live execution gate. SDC-ADR-012's execution-day evidence requirement remains in force.

This change introduces only the contracts, generated schema, in-memory canonical builder, and
read-only resolver. It does not migrate, rewrite, delete, or deduplicate the R2-R6 archives. A
later build may add a fail-closed legacy importer and writer after compatibility testing; until
then the old archives remain the authoritative materialized records.

## Exclusions and consequences

An `EvidenceBundle` is an integrity container, not a content-classification or secret-scanning
system. A future writer/importer must apply an explicit admission policy that excludes
`LiveAuthorization`, nonce, API Key, credential, Provider request or response, task ID, generated
media, Worker state, Temporal history, database rows, and spend authority before anchoring a
bundle. This read-only build does not claim that arbitrary caller-supplied bytes are safe merely
because their hashes validate. Bundle identity is not a request fingerprint, contract hash,
archive tree hash, or authorization. Creating, verifying, or resolving a bundle performs no
network call and grants no permission to start services or contact Ark.

R6 remains an expired historical archive. Its prior pricing snapshot remains structurally
parseable, but the newer R6-calibrated 196425-token live cost floor still applies independently;
evidence reuse cannot restore the old snapshot's live eligibility.
