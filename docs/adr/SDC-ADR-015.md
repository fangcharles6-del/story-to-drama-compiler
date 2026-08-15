# SDC-ADR-015: Restricted verified-origin import of R2-R6 evidence

- **Status:** Accepted
- **Date:** 2026-08-14
- **Version:** V01

## Decision

SDC may materialize selected historical evidence from the immutable Canary R2-R6 archives into
the content-addressed store defined by SDC-ADR-014. This is a bounded, offline compatibility path,
not a general archive importer. The source archive, its outer index, and a caller-supplied expected
SHA-256 of that outer index are separate inputs. The importer must verify the supplied index digest
before trusting any digest or path obtained from the index or manifest. A digest read from the same
index or manifest is self-consistency evidence only and is never a trust anchor.

Legacy verification is round-specific and fail-closed:

- **R2 is degraded and requires the R3 chain.** R2's own outer index does not carry a tree digest
  or algorithm. An R2 import therefore also requires a verified R3 provenance chain that binds the
  R2 outer index, manifest, freeze report, file count, and derived tree. Standalone inspection is
  `DEGRADED`; a successful R3-linked import is `CHAIN_COMPAT`, never
  `FULL_DESCRIPTOR_TREE`.
- **R3 uses one exact compatibility rule.** Its outer index carries a tree digest but omits the
  algorithm name. Only the reviewed V02-R3 shape may map that omission to
  `compact-json-array-v1`; the importer must not infer an algorithm for any other archive or shape.
- **R4, R5, and R6 require full descriptor-tree verification.** Their independently anchored outer indexes must
  explicitly name `compact-json-array-v1`, and the computed tree digest, manifest digest, freeze
  report digest, and file count must all match before any member is admitted.

Verification of a complete legacy tree does not admit the complete tree into the CAS. Each round
has a reviewed, exact path allowlist. Materialization is limited to sanitized PDF, PNG, or JPEG
evidence and to JSON evidence whose role is capability, pricing, entitlement, or telemetry. Index,
manifest, and freeze-report files may be read as verification metadata but are not automatically
evidence members. Unknown paths, extensions, media types, semantic roles, duplicate paths,
case-insensitive collisions, links, junctions, reparse points, or digest and byte-count drift fail
closed. References to prior rounds or historical paths remain metadata and are never followed as
filesystem paths.

`FULL_DESCRIPTOR_TREE` means that the independently anchored descriptor tree is complete and every admitted
evidence object's bytes were read and verified. Excluded application/request/runtime files are
deliberately not opened: their regular-file type and declared size are checked, while their
anchored manifest descriptors participate in reconstruction of the legacy tree. This distinction
is reported per file and prevents “full verification” from becoming permission to inspect excluded
Provider or execution content.

Every imported capture uses acquisition `LEGACY_IMPORT`. The importer preserves the original
capture time and `valid_until` without rounding, replacement, or extension, and records the
verified origin anchor. Importing, copying, re-anchoring, or deduplicating bytes never changes their
freshness. An expired capture or bundle remains historical forever and cannot satisfy a current
evidence check or authorize execution.

## Atomic materialization

The source archive is opened read-only. Admitted objects are copied into a private staging area,
hashed and size-checked during the copy, and promoted to their SHA-256 CAS locations atomically.
An existing CAS object must be verified byte-for-byte and must never be overwritten on mismatch.
The EvidenceBundle manifest is constructed and published only after every admitted object and the
complete verified-origin record have succeeded. Failure before that final publication must leave
  no discoverable complete bundle. Bundle `created_at` is derived from the latest anchored capture,
  not wall-clock import time, so repeating an import with the same source and anchor must produce
  the same bundle ID and CAS layout.

The canonical R2-R6 directories remain the authoritative materialized archives. Import does not
modify, rename, delete, chmod, rewrite, repair, or deduplicate any historical file. It also does not
change an outer index, insert a new trust anchor into an old round, or reinterpret a degraded round
as fully verified.

## Admission and execution boundary

Before opening a candidate evidence file, the importer must apply the round path allowlist and
reject forbidden names and roles. This path never reads or copies the R6 live directory, an API
Key, credential, `LiveAuthorization`, authorization nonce or body, Provider request or response,
Provider task ID, generated result media, Worker state, Temporal history, database rows, or spend
authority. In particular, `.artifacts/canary/v02-r6-live` is outside the importer root and must not
be traversed for verification or materialization.

This decision does not connect EvidenceBundle to the Canary live gate, create or consume an
authorization, inject a secret, start a Worker or local service, access Ark, issue a Provider
request, recharge, purchase, claim a trial, or perform paid generation. R6 and all earlier rounds
remain expired historical evidence. Their import cannot restore live eligibility, extend the old
pricing snapshot, or replace the execution-day evidence required by SDC-ADR-012 and SDC-ADR-013.

## Acceptance criteria

- Tests bind each supported fixture to an independently supplied outer-index SHA-256 and reject a
  self-derived or mismatched anchor.
- Compatibility tests prove the R2 degraded/R3-chain rule, the exact R3 missing-algorithm rule, and
  full R4-R6 tree, manifest, report, and file-count verification.
- Admission tests prove that only the per-round PDF, PNG, JPEG, capability JSON, pricing JSON,
  entitlement JSON, and telemetry JSON allowlists can reach staging or CAS.
- Malicious path, duplicate-key, link or reparse-point, digest, byte-count, unknown-algorithm,
  undeclared-file, partial-write, and existing-object mismatch cases fail closed.
- A repeated successful import is deterministic and idempotent, while an interrupted import never
  publishes a complete manifest.
- Imported timestamps and expiry values round-trip unchanged, and every expired `LEGACY_IMPORT`
  bundle is rejected by current/live eligibility checks.
- Tests and implementation perform no network request, service startup, database mutation,
  credential inspection, Provider call, or write to any R2-R6 or R6-live archive.
