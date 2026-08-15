# Canonical R2-R6 evidence CAS

This procedure materializes the reviewed Canary R2-R6 evidence into one immutable,
content-addressed store. It is an offline historical migration only. It does not make expired
evidence current and does not authorize a Canary, an API Key, a Worker, or an Ark request.

## Fixed boundaries

- Source: `.artifacts/canary/v02-r2` through `.artifacts/canary/v02-r6` plus their adjacent outer
  indexes. The command uses the reviewed anchors compiled into SDC; operators cannot override
  them.
- Destination: `.artifacts/evidence-cas/v1`, outside the Canary container.
- The destination parent must be a real, local directory controlled by the current operator. Do
  not run concurrent materializers or allow another process to mutate that parent during publish.
- Excluded: `.artifacts/canary/v02-r6-live`, authorizations, credentials, Provider requests or
  responses, generated media, Worker state, Temporal history, and database state.
- Source archives are read-only inputs. The command never repairs, rewrites, deletes, or
  deduplicates them in place.

## Verify before writing

From a clean checkout of the reviewed SDC revision, run:

```powershell
uv run python -m sdc.legacy_evidence_materialize `
  --canary-root .artifacts/canary `
  --output-root .artifacts/evidence-cas/v1
```

This is the default verify-only mode. It must validate all five independent outer-index anchors,
the R2-to-R3 compatibility chain, each reviewed descriptor tree, and the expected deterministic
bundle IDs. It creates no output directory.

## Materialize once

Only after verify-only succeeds, run the same command with the explicit write gate:

```powershell
uv run python -m sdc.legacy_evidence_materialize `
  --canary-root .artifacts/canary `
  --output-root .artifacts/evidence-cas/v1 `
  --apply
```

The command builds the complete set in a sibling staging directory and verifies it again. It then
claims a new destination, publishes every file with no-replace semantics, and links the
deterministic `catalog.json` last as the commit marker. There is no `--force`, repair, or
anchor-override mode. An unexpected existing destination, lock, digest drift, unknown publication
result, or partial staging result enters `HUMAN_GATE`.

Expected closure:

- five manifests: `bundles/v02-r2.json` through `bundles/v02-r6.json`;
- 67 unique content-addressed objects;
- member counts `22, 22, 29, 29, 27` for R2 through R6;
- first materialization writes `22, 3, 10, 5, 27` new objects by round;
- every capture remains `LEGACY_IMPORT` with its original validity limit.

Run verify-only again after publication. A repeated `--apply` may only verify the existing store;
it must not overwrite, merge, repair, or publish additional bytes.

## Execution boundary

The canonical store prevents repeated copying and re-review of unchanged historical bytes. It is
not a freshness source. R2-R6 remain expired, and `EvidenceBundleReader.assert_current()` must
continue to reject them. Any future live operation still requires new execution-day `FRESH`
evidence and a separate, exact-request `LiveAuthorization`.
