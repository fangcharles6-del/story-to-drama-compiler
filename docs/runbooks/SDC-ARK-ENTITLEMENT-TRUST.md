# Ark Canary entitlement trust (candidate-only)

This runbook covers PR1 of proposed SDC-ADR-018. It is an offline candidate-freezing and
verification procedure, not an Ark execution procedure. The positive entitlement registry is
intentionally empty in this delivery, so no candidate can be loaded as trusted and no Key,
service, authorization, console access or Provider request is enabled.

## Fixed profile

`ark-canary-entitlement-v1` binds exactly:

- Provider `volcengine_ark`;
- model `doubao-seedance-2-0-260128`;
- region `cn-beijing`;
- operation `contents.generations.tasks.create`;
- observed state `ENABLED`; and
- conclusion `PASS_ENTITLEMENT_ONLY`.

The EvidenceBundle has exactly two distinct objects and one `FRESH` capture with no predecessor
or origin:

- `evidence/entitlement.pdf`, role `entitlement.evidence`, `application/pdf`; and
- `snapshots/entitlement.json`, role `entitlement.snapshot`, `application/json`, schema `1.0.0`.

The PDF is capped at 16 MiB and is structurally rejected if encrypted or if it contains an
attachment, form, JavaScript, open/additional action, external URI or other interactive action.
The JSON is strict UTF-8 and capped at 64 KiB; duplicate keys, non-finite values and extra fields
fail closed. Mechanical validation does not replace the independent visual privacy review needed
before any future registry entry.

## Pseudonymous scope bindings

Account scope is normalized from exactly `account_id`, `subaccount_id` and `project_id` and hashed
with the ADR-018 account-scope domain plus a reviewer-controlled 32-byte private salt. Credential
metadata is normalized from exactly `secret_store`, `resource_locator` and `immutable_version` and
hashed under its separate domain. The raw identifiers, locator and salt remain outside Git, the
CAS, command arguments and logs. The Key value is never an input to either function.

The snapshot and registry store only the resulting lowercase SHA-256 values. They are
pseudonymous metadata, not proof that a Key belongs to the account. A future deployment review
must establish that relationship independently.

## Offline candidate freeze

Prepare only two already-sanitized, ordinary local files in a new path outside every Canary,
historical evidence and current capability/pricing store. Do not use links, junctions, mapped or
network paths. The local parent must remain under the sole operator's control: no concurrent
process may rename, replace or relink it while freezing or loading. Static link/reparse checks do
not claim protection against an equally privileged process racing filesystem operations. The
snapshot's evidence digest must equal the exact PDF bytes.

The offline entrypoint is:

```text
uv run --offline --no-sync python -B -m sdc.ark_entitlement \
  --snapshot <new-local-entitlement-snapshot.json> \
  --evidence-pdf <new-local-sanitized-entitlement.pdf> \
  --output-root .artifacts/entitlement-current/v1
```

It does not consult or modify the registry and reads no environment secret, account service or
network endpoint. It validates all inputs before writing, publishes content-addressed objects
without replacement, verifies the full object closure and publishes the manifest last. Repeating
the exact candidate is idempotent; conflicting existing bytes fail closed. Output mode is
`candidate-only-not-trusted`.

The freezer never edits `REVIEWED_ARK_ENTITLEMENT_EVIDENCE`. A future exact entry requires its own
reviewed commit and must contain only normalized digests and timestamps. That entitlement review
must be merged before a later, separate authorization review.

## Validity and trust loading

Validity ends no later than the earliest of the declared source boundary, four hours after
capture and `23:59:59+08:00` on the capture date. The upper boundary is exclusive. Copying,
repackaging or reviewing a bundle cannot renew it; renewal requires a new observation and a new
bundle.

The trusted loader first resolves the caller-selected exact bundle ID in the source-controlled
positive registry. Empty, unknown, duplicate, not-yet-reviewed or expired entries fail before the
manifest or CAS paths are inspected. Only then does it validate the fixed layout, exact profile,
all object bytes, canonical snapshot, PDF structure and every bundle/capture/snapshot/registry
mapping. It checks the exclusive deadline again after full verification.

In this PR the registry is empty by design, so every trusted-load attempt fails before disk access.
No `TrustedArkEntitlement` can be produced from the committed state.

## Stop conditions

Stop without relabeling, extending, overwriting or adding a registry entry on any malformed PDF or
JSON, privacy-review uncertainty, path/link/reparse finding, digest or field drift, non-exact
profile, CAS conflict, unknown/duplicate registry identity, future timestamp, or expiry. This
runbook contains no authorization creation, Key handling, service startup, Ark/console access,
purchase, trial, recharge or POST procedure.
