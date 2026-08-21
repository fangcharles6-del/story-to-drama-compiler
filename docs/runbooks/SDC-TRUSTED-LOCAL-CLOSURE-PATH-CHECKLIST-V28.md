# Trusted-local Closure Path Checklist v2.8

## Purpose and status

This runbook implements SDC-ADR-029. It defines one read-only helper that converts one explicit,
bounded seed and one exact frozen Pack Manifest into a deterministic, parameter-labelled checklist
for manual review of an existing v2.7 finalizer path interface.

The helper solves a transcription problem only. It does not validate artifact contents, verify a
rights closure, prove identity, establish currentness, invoke a finalizer, write an artifact or
grant authority. Its strongest status is:

```text
PATH_CHECKLIST_READY_FOR_HUMAN_REVIEW_ONLY
```

Source and test implementation is approved with synthetic temporary data only. A checkout that
contains this module is not approved to read a real Pack, Manifest, Use Plan, Review Record,
identity reference or authoring input. Every real invocation, commit, push, PR, merge and Provider
operation remains separately controlled.

## Module and command

The module is:

```text
sdc.real_asset_closure_path_checklist_v28
```

Its only CLI operation is checklist generation:

```text
python -m sdc.real_asset_closure_path_checklist_v28 render-checklist --seed <absolute-seed-json>
```

`--seed` is required exactly once. There is no standard-input, environment-variable,
directory, default-root, URL or inline-JSON alternative. The operation writes one JSON object to
standard output on success and creates no file.

The generator exposes no finalizer wrapper. In particular, it has no `--execute`, `--output`,
`--checklist-output`, `--approve`, `--current`, `--provider`, `--latest` or pass-through argument.
It does not accept expected artifact IDs or SHA-256 values, timestamps, authoring text, credentials
or authority flags.

The public Python surface is deliberately one-way:

```text
ClosurePathChecklistEntryV28
TrustedLocalClosurePathChecklistV28
TrustedLocalClosurePathChecklistError
build_closure_path_checklist_v28(seed_path)
main
```

The two result classes are frozen operational dataclasses, not Pydantic artifacts or committed
Schemas. No public function converts their entries into a v2.7 finalizer path dataclass or invokes
a target command.

## Fixed profile and command matrix

The seed selects one exact profile and one exact v2.7 target command. Only these combinations are
accepted:

| Profile | `target_finalizer_module` | Allowed `target_command` | Entries |
|---|---|---|---:|
| `USE_PLAN_29` | `sdc.real_asset_use_plan_finalizer_v27` | `inspect-use-plan-ready` | 29 |
| `USE_PLAN_29` | `sdc.real_asset_use_plan_finalizer_v27` | `finalize-use-plan` | 29 |
| `REVIEW_REQUEST_32` | `sdc.real_asset_use_scope_review_finalizer_v27` | `preflight-review-request` | 32 |
| `REVIEW_INSTRUCTION_34` | `sdc.real_asset_use_scope_review_finalizer_v27` | `preflight-review-instruction` | 34 |
| `REVIEW_INSTRUCTION_34` | `sdc.real_asset_use_scope_review_finalizer_v27` | `finalize-review-record` | 34 |
| `REVIEW_RECORD_VERIFICATION_33` | `sdc.real_asset_use_scope_review_finalizer_v27` | `verify-review-record` | 33 |

Every row binds `target_finalizer_version=v2.7`. Seed module, version and target command values are exact
equality guards against the hard-coded profile descriptor; they cannot extend or override it.

`verify-use-plan` is not supported because its 30-entry closure is outside the four accepted v2.8
profiles. Rights Manifest operations, unknown commands and any later finalizer version are also
outside this release. The tool must fail closed rather than infer a near match.

The checklist covers existing filesystem source arguments only. It deliberately excludes absent
create-new output paths, expected ID/SHA guards and explicit time values. Their omission is not a
default or approval; they must be separately selected and approved for a later finalizer operation.

## Seed transport

The seed is a hostile transport object, not an SDC artifact. It must be an explicitly selected,
fully qualified, existing ordinary local file outside every Git tree. It is read with a fixed
65,536-byte maximum. The parser requires UTF-8 without BOM and rejects:

- empty or oversized input;
- malformed UTF-8 or a UTF-8 BOM;
- duplicate or unknown keys;
- a missing profile-required key;
- a key not applicable to the selected profile;
- non-string paths, coercion, `null` or arrays where a string path is required;
- non-finite JSON values; and
- a profile, target command, count, version or module not in the fixed matrix.

Ordinary JSON whitespace is allowed. Both LF and CRLF line endings are accepted. The seed need not
use the canonical artifact indentation form because the raw seed is not retained or hashed as an
artifact.

Every string must already be exact: the parser does not trim, Unicode-normalize, expand an
environment variable, expand `~`, evaluate shell syntax or repair a path. A malformed or ambiguous
value fails closed.

### Exact top-level seed members

Every seed contains exactly these seven members:

| Member | Exact meaning |
|---|---|
| `schema_version` | literal `1.0.0` |
| `document_type` | literal `sdc.trusted-local-closure-path-checklist-seed` |
| `profile` | one of the four fixed profile names |
| `target_finalizer_module` | exact module from the profile matrix |
| `target_finalizer_version` | literal `v2.7` |
| `target_command` | one command allowed by the selected profile |
| `explicit_paths` | one object whose keys exactly equal the profile's explicit path arguments |

`target_finalizer_module`, `target_finalizer_version` and `target_command` are comparison-only
guards. They do not make the target dynamic and are never imported or executed.

### Common `explicit_paths` members

All profiles require these exact keys, including the leading `--`:

| `explicit_paths` key | Generated argument |
|---|---|
| `--pack-root` | `--pack-root` |
| `--evidence` | `--evidence` |
| `--reviewer-a` | `--reviewer-a` |
| `--reviewer-b` | `--reviewer-b` |
| `--pair-check` | `--pair-check` |
| `--evidence-retained-record` | `--evidence-retained-record` |
| `--evidence-preparer-ref` | `--evidence-preparer-ref` |
| `--reviewer-a-retained-record` | `--reviewer-a-retained-record` |
| `--reviewer-b-retained-record` | `--reviewer-b-retained-record` |
| `--qualification-request` | `--qualification-request` |
| `--qualifier-ref` | `--qualifier-ref` |
| `--qualification-instruction` | `--qualification-instruction` |
| `--qualification-decision` | `--qualification-decision` |
| `--rights-manifest-file` | `--rights-manifest-file` |

The seed does not contain `--pack-manifest` or `--media-path`. Those values can only be derived as
specified below. A supplied derivation override is an extra key and fails closed.

### Profile-specific `explicit_paths` members

| Profile | Additional required keys |
|---|---|
| `USE_PLAN_29` | none |
| `REVIEW_REQUEST_32` | `--use-plan-file`, `--maker-identity-ref`, `--maker-input` |
| `REVIEW_INSTRUCTION_34` | `--use-plan-file`, `--maker-identity-ref`, `--maker-input`, `--checker-identity-ref`, `--checker-input` |
| `REVIEW_RECORD_VERIFICATION_33` | `--use-plan-file`, `--maker-identity-ref`, `--checker-identity-ref`, `--review-record-file` |

The verification profile rejects `--maker-input` and `--checker-input`; v2.7 historical
verification does not read them. The Request profile rejects Checker fields. The Use Plan profile
rejects every Review field.

### Synthetic 34-entry seed shape

The following illustrates field shape only. It is not a real-data approval and its paths must be
replaced by isolated synthetic test paths:

```json
{
  "document_type": "sdc.trusted-local-closure-path-checklist-seed",
  "explicit_paths": {
    "--checker-identity-ref": "C:\\synthetic\\checker-identity\\identity.md",
    "--checker-input": "C:\\synthetic\\checker-authoring\\input.json",
    "--evidence": "C:\\synthetic\\evidence\\bundle.json",
    "--evidence-preparer-ref": "C:\\synthetic\\refs\\preparer.md",
    "--evidence-retained-record": "C:\\synthetic\\retained\\evidence.md",
    "--maker-identity-ref": "C:\\synthetic\\maker-identity\\identity.md",
    "--maker-input": "C:\\synthetic\\maker-authoring\\input.json",
    "--pack-root": "C:\\synthetic\\frozen\\synthetic_pack",
    "--pair-check": "C:\\synthetic\\reviews\\pair.json",
    "--qualification-decision": "C:\\synthetic\\qualification-decision\\decision.json",
    "--qualification-instruction": "C:\\synthetic\\qualification-instruction\\instruction.json",
    "--qualification-request": "C:\\synthetic\\qualification-request\\request.json",
    "--qualifier-ref": "C:\\synthetic\\refs\\qualifier.md",
    "--reviewer-a": "C:\\synthetic\\reviews\\a.json",
    "--reviewer-a-retained-record": "C:\\synthetic\\retained\\a.md",
    "--reviewer-b": "C:\\synthetic\\reviews\\b.json",
    "--reviewer-b-retained-record": "C:\\synthetic\\retained\\b.md",
    "--rights-manifest-file": "C:\\synthetic\\manifest\\rights.json",
    "--use-plan-file": "C:\\synthetic\\plan\\use-plan.json"
  },
  "profile": "REVIEW_INSTRUCTION_34",
  "schema_version": "1.0.0",
  "target_command": "preflight-review-instruction",
  "target_finalizer_module": "sdc.real_asset_use_scope_review_finalizer_v27",
  "target_finalizer_version": "v2.7"
}
```

## Deterministic Pack derivation

The `explicit_paths["--pack-root"]` value is admitted as one ordinary local directory. The
generator then forms exactly:

```text
<admitted --pack-root>/asset-pack.json
```

It does not enumerate the Pack root. The resulting exact path must pass the same safe-file
admission rules as other file entries. That path is output as `--pack-manifest` with
`source=MANIFEST_DERIVED`.

The Pack Manifest is read as bounded strict canonical Pack JSON and must contain exactly fourteen
ordered object descriptors accepted by its existing immutable contract.
For descriptor occurrence `n`, the generator:

1. takes only `manifest.objects[n].object_path`;
2. parses it as a safe relative POSIX path;
3. rejects absolute, empty, dot, parent-traversal, drive, device and ambiguous components;
4. joins its components to the admitted Pack root;
5. requires the result to remain physically under that Pack root;
6. requires its observed file size to equal the descriptor's `size_bytes`; and
7. admits it as the existing ordinary file for `--media-path` occurrence `n`.

Manifest order is authoritative for ordering only. The generator does not sort hashes, inspect an
object directory, infer a shard path from a digest or accept a seed-supplied media override.

The generator does not claim that any media bytes match a Manifest digest. That content proof is
reserved for the independently invoked v2.7 finalizer.

## Exact entry order

`ordinal` is zero-based. `occurrence` is zero for a non-repeated argument. The common 29-entry
prefix is:

| Ordinal | `argument_name` | Occurrence | Source | Value source |
|---:|---|---:|---|---|
| 0 | `--pack-root` | 0 | `EXPLICIT` | `explicit_paths["--pack-root"]` |
| 1 | `--pack-manifest` | 0 | `MANIFEST_DERIVED` | exact `asset-pack.json` under Pack root |
| 2 | `--media-path` | 0 | `MANIFEST_DERIVED` | `objects[0].object_path` |
| 3 | `--media-path` | 1 | `MANIFEST_DERIVED` | `objects[1].object_path` |
| 4 | `--media-path` | 2 | `MANIFEST_DERIVED` | `objects[2].object_path` |
| 5 | `--media-path` | 3 | `MANIFEST_DERIVED` | `objects[3].object_path` |
| 6 | `--media-path` | 4 | `MANIFEST_DERIVED` | `objects[4].object_path` |
| 7 | `--media-path` | 5 | `MANIFEST_DERIVED` | `objects[5].object_path` |
| 8 | `--media-path` | 6 | `MANIFEST_DERIVED` | `objects[6].object_path` |
| 9 | `--media-path` | 7 | `MANIFEST_DERIVED` | `objects[7].object_path` |
| 10 | `--media-path` | 8 | `MANIFEST_DERIVED` | `objects[8].object_path` |
| 11 | `--media-path` | 9 | `MANIFEST_DERIVED` | `objects[9].object_path` |
| 12 | `--media-path` | 10 | `MANIFEST_DERIVED` | `objects[10].object_path` |
| 13 | `--media-path` | 11 | `MANIFEST_DERIVED` | `objects[11].object_path` |
| 14 | `--media-path` | 12 | `MANIFEST_DERIVED` | `objects[12].object_path` |
| 15 | `--media-path` | 13 | `MANIFEST_DERIVED` | `objects[13].object_path` |
| 16 | `--evidence` | 0 | `EXPLICIT` | `explicit_paths["--evidence"]` |
| 17 | `--reviewer-a` | 0 | `EXPLICIT` | `explicit_paths["--reviewer-a"]` |
| 18 | `--reviewer-b` | 0 | `EXPLICIT` | `explicit_paths["--reviewer-b"]` |
| 19 | `--pair-check` | 0 | `EXPLICIT` | `explicit_paths["--pair-check"]` |
| 20 | `--evidence-retained-record` | 0 | `EXPLICIT` | `explicit_paths["--evidence-retained-record"]` |
| 21 | `--evidence-preparer-ref` | 0 | `EXPLICIT` | `explicit_paths["--evidence-preparer-ref"]` |
| 22 | `--reviewer-a-retained-record` | 0 | `EXPLICIT` | `explicit_paths["--reviewer-a-retained-record"]` |
| 23 | `--reviewer-b-retained-record` | 0 | `EXPLICIT` | `explicit_paths["--reviewer-b-retained-record"]` |
| 24 | `--qualification-request` | 0 | `EXPLICIT` | `explicit_paths["--qualification-request"]` |
| 25 | `--qualifier-ref` | 0 | `EXPLICIT` | `explicit_paths["--qualifier-ref"]` |
| 26 | `--qualification-instruction` | 0 | `EXPLICIT` | `explicit_paths["--qualification-instruction"]` |
| 27 | `--qualification-decision` | 0 | `EXPLICIT` | `explicit_paths["--qualification-decision"]` |
| 28 | `--rights-manifest-file` | 0 | `EXPLICIT` | `explicit_paths["--rights-manifest-file"]` |

The Request and Instruction profiles append:

| Ordinal | Profile membership | `argument_name` | Occurrence | Source | Seed key |
|---:|---|---|---:|---|---|
| 29 | Request, Instruction | `--use-plan-file` | 0 | `EXPLICIT` | `explicit_paths["--use-plan-file"]` |
| 30 | Request, Instruction | `--maker-identity-ref` | 0 | `EXPLICIT` | `explicit_paths["--maker-identity-ref"]` |
| 31 | Request, Instruction | `--maker-input` | 0 | `EXPLICIT` | `explicit_paths["--maker-input"]` |
| 32 | Instruction only | `--checker-identity-ref` | 0 | `EXPLICIT` | `explicit_paths["--checker-identity-ref"]` |
| 33 | Instruction only | `--checker-input` | 0 | `EXPLICIT` | `explicit_paths["--checker-input"]` |

The verification profile appends a different four-entry suffix to the common prefix:

| Ordinal | `argument_name` | Occurrence | Source | Seed key |
|---:|---|---:|---|---|
| 29 | `--use-plan-file` | 0 | `EXPLICIT` | `explicit_paths["--use-plan-file"]` |
| 30 | `--maker-identity-ref` | 0 | `EXPLICIT` | `explicit_paths["--maker-identity-ref"]` |
| 31 | `--checker-identity-ref` | 0 | `EXPLICIT` | `explicit_paths["--checker-identity-ref"]` |
| 32 | `--review-record-file` | 0 | `EXPLICIT` | `explicit_paths["--review-record-file"]` |

No implementation may generate this order by sorting seed keys. It is compiled from the fixed
profile descriptor.

## Path admission

Every path goes through the v2.7-aligned trusted-local admission boundary before rendering. The
operation rejects, as applicable:

- relative and empty paths;
- UNC, network, device and extended-device namespaces;
- alternate data streams;
- symbolic links, junctions and reparse points in any existing component;
- non-anchor mounts and bind mounts;
- hard-linked files or non-regular objects;
- a missing target or wrong directory/file kind;
- lexical, case-folded, resolved or physical duplication;
- Pack media outside Pack root; and
- repository paths, including repository `output/` and `tmp/`.

The generator never reads selected target contents other than the seed and Pack Manifest. Metadata
and handle identity inspection needed for path admission is not a content-validation claim.

All entries in a selected profile must be mutually distinct under lexical, Windows
case-insensitive and physical identity checks. The fixed Pack containment relationship among Pack
root, Pack Manifest and media is intentional; no explicit external file may be inside the Pack.

The helper does not reproduce v2.7 filename-suffix, outcome-token or artifact-content validation.
Passing checklist admission therefore does not claim that a path will pass the later finalizer;
the separately authorized v2.7 operation must perform those checks itself.

## Windows rendering rules

Rendering follows admission and is deterministic:

1. use the admitted resolved `Path` value;
2. emit Windows separators as `\`;
3. remove trailing separators from ordinary paths;
4. preserve the required separator in a drive root such as `C:\`;
5. do not call `normcase()` or proactively change letter case; and
6. use case-insensitive comparison only to reject aliases.

The displayed path is therefore suitable for one-to-one manual mapping to the named v2.7
parameter. It is not a promise that the path will remain unchanged until execution.

## Capture and TOCTOU sequence

One generation attempt performs this fixed sequence:

1. safely admit, open and capture the exact seed;
2. strictly parse its fixed profile and explicit values;
3. admit Pack root and the exact derived Pack Manifest path;
4. safely open and capture the Manifest;
5. derive exactly fourteen ordered media paths;
6. admit every fixed profile entry and reject all aliases;
7. build the ordered canonical digest envelope;
8. recapture the seed and Manifest and require identity, size, metadata and exact-byte digest
   equality with their first captures;
9. recheck admitted path identities needed to detect replacement during generation; and
10. emit one success JSON object.

Any drift or uncertainty fails closed. The generator does not retry, repair, recanonicalize a
source file, pick a replacement, or emit a partial list. Because it never creates an artifact,
there is no rollback or quarantine mode.

The recapture covers one generator process only. It does not preserve a snapshot for a future
finalizer operation.

## Digest envelope

The implementation constructs an internal object with exactly:

```json
{
  "entries": [
    {
      "argument_name": "<exact v2.7 parameter>",
      "occurrence": 0,
      "ordinal": 0,
      "path": "<admitted rendered absolute path>",
      "source": "EXPLICIT"
    }
  ],
  "entry_count": 29,
  "profile": "<fixed profile>",
  "target_command": "<fixed command>",
  "target_finalizer_module": "<fixed v2.7 module>",
  "target_finalizer_version": "v2.7"
}
```

The example shows shape, not a complete list. The full `entries` array must match the selected
fixed count and order.

The digest envelope contains only the six top-level members shown above. It is serialized with
`ensure_ascii=False`, sorted keys, two-space indentation, separators `(",", ": ")` and exactly one
final LF. `path_list_sha256` is the lowercase SHA-256 of those exact canonical bytes.

The digest does not include raw seed bytes or their LF/CRLF choice. It does not bind source file
contents, Pack Manifest digest, filesystem identities, timestamps or a later invocation. It must
never be accepted as an expected content guard by a finalizer.

## Success output

Success writes exactly one compact sorted-key UTF-8 JSON object plus one LF to standard output and
nothing to standard error. Its fields are:

```json
{
  "automated_execution_allowed": false,
  "current_gate": "HUMAN_GATE",
  "document_type": "sdc.trusted-local-closure-path-checklist",
  "entries": [],
  "entry_count": 32,
  "execution_authorized": false,
  "generator_version": "v2.8",
  "manual_confirmation_required": true,
  "path_format": "WINDOWS_BACKSLASH",
  "path_list_sha256": "<lowercase 64-hex digest>",
  "posts_allowed": 0,
  "profile": "REVIEW_REQUEST_32",
  "provider_requests": 0,
  "provider_state": "NOT_AUTHORIZED",
  "schema_version": "1.0.0",
  "status": "PATH_CHECKLIST_READY_FOR_HUMAN_REVIEW_ONLY",
  "target_command": "preflight-review-request",
  "target_finalizer_module": "sdc.real_asset_use_scope_review_finalizer_v27",
  "target_finalizer_version": "v2.7",
  "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
}
```

`entries` is shown empty only to keep the example bounded; real success requires exactly
`entry_count` entries.

The output contains no shell command, executable `argv`, response file, seed path, source digest,
human text, identity contents, credentials, Provider selection or authority-bearing language.

## Failure output

Any rejected seed, unsafe path, descriptor mismatch, unknown version, wrong count, alias, drift or
serialization invariant produces no standard output. Standard error receives only one bounded
generic object:

```json
{"error":"FAILED_CLOSED"}
```

The process exits nonzero. A failure does not include a private path, seed field value, Manifest
content, system exception text or partially generated entry. There is no automatic retry.

Argument-parser usage text must not echo a seed value. Parser failure remains fail-closed and must
not read unrelated private sources.

## Mandatory manual workflow

A permitted future real use would still require separate approvals and these distinct stages:

1. a human prepares and reviews an exact seed for one fixed profile and command;
2. a separate one-time authorization names that seed and permits one read-only generation;
3. the generator emits the manual-review-only checklist and stops;
4. a human inspects every ordinal, argument name, occurrence, path, source and version binding;
5. a later authorization independently names every explicit finalizer path, time, expected
   fingerprint and output where applicable; and
6. the v2.7 finalizer independently reopens and validates its complete closure.

Stage 3 may not automatically trigger stage 5 or 6. `path_list_sha256` may be quoted in an audit
note to identify what the human viewed, but it cannot replace the paths or any finalizer guard.

## Prohibited integration

Project code and operational documentation must not:

- pipe checklist stdout into a finalizer;
- parse a checklist into a v2.7 path dataclass;
- add `--checklist`, `--seed` or `--path-list-sha256` to a finalizer;
- generate a finalizer command, shell fragment, response file or executable argument array;
- monitor a directory and execute when a checklist appears;
- store checklist output as workflow authority or mutable latest/current state;
- treat an accepted path as accepted bytes;
- infer current rights, identity, entitlement or Provider availability; or
- combine generation and execution under one API call.

The checklist types remain operational display types and are not Pydantic contracts or committed
Schemas.

## Synthetic implementation test matrix

All tests use isolated synthetic temporary directories. No test may read repository `output/` or
`tmp/`, a user document area, network location or Provider service.

### Profile and mapping tests

- `USE_PLAN_29` has exactly ordinals 0 through 28.
- `REVIEW_REQUEST_32` has exactly ordinals 0 through 31.
- `REVIEW_INSTRUCTION_34` has exactly ordinals 0 through 33.
- `REVIEW_RECORD_VERIFICATION_33` has exactly ordinals 0 through 32.
- Every argument name matches the v2.7 CLI exactly.
- Non-repeated arguments have occurrence zero.
- `--media-path` has occurrences 0 through 13 in Manifest order.
- Request, Instruction and verification suffixes match the tables above.
- Inapplicable seed fields and wrong profile/target-command combinations fail.

### Seed tests

- LF and CRLF representations of the same object produce identical output.
- Reordered JSON keys produce identical output.
- BOM, invalid UTF-8, duplicate key, unknown key, missing key, `null`, coercion, empty and oversized
  seeds fail.
- Raw seed formatting is absent from `path_list_sha256`.
- Seed replacement or mutation at every capture boundary fails.

### Manifest and derivation tests

- `asset-pack.json` is joined directly without directory enumeration.
- Exactly fourteen media paths are derived from ordered `object_path` values.
- Reorder, missing object, extra object, absolute path, traversal, escape and unsafe component fail.
- No media path may be supplied in the seed.
- Media content is not interpreted as a rights proof.

### Path safety tests

- relative, UNC, device, alternate-stream, missing and wrong-kind paths fail;
- symlink, junction, reparse point, hard link, mount and bind-mount cases fail where supported;
- lexical, case-folded and physical aliases fail;
- Pack escape and an explicit external file inside the Pack fail;
- slash and trailing-separator variants render deterministically;
- drive roots retain their required separator; and
- input letter case is not proactively changed.

### No-discovery and no-side-effect tests

Tests must monkeypatch the applicable APIs to prove no call to:

```text
Path.glob
Path.rglob
Path.iterdir
glob.glob
glob.iglob
os.listdir
os.scandir
os.walk
```

They must also prove no output file, temporary receipt, directory, ACL change, clock read, network
call, Provider call or v2.7 finalizer invocation occurs.

### Version, digest and authority tests

- every matrix row emits target module/version/command/profile exactly;
- unknown target version, module, command, count, parameter name, occurrence or order is unreachable or
  fails closed;
- canonical envelope digests are stable across processes;
- path reorder or target-command change changes the digest;
- all manual-only and zero-authority fields are present with exact values;
- no success language implies content verification or execution readiness; and
- all committed Schemas remain normalized-LF byte-identical.

## Validation sequence

The synthetic-only implementation is complete only after:

1. the focused v2.8 tests pass;
2. Ruff formatting and lint pass;
3. strict Mypy passes;
4. the changed-file scope contains only the separately approved v2.8 files;
5. all existing Schema bytes are unchanged; and
6. full offline `make check` passes in a fresh LF-preserving isolated worktree that excludes the
   repository `output/` and `tmp/` directories.

Passing validation establishes implementation behavior against synthetic fixtures only. It is not
approval for a real checklist operation, finalizer operation, Provider action, commit or release.

## Incident handling

An unexpected source, alias, drift, parser condition or platform behavior is a fail-closed result.
The operator must not retry with a broader path, scan for a replacement, edit source permissions,
rewrite line endings, change profile or invoke a finalizer under the same approval. Diagnosis and
any remediation require a new bounded authorization.

Because the generator writes no artifact, failure has no rollback path. If external software
captured a partial standard-output stream, that partial data is not a checklist and must not be
used.

## Authority boundary

Every result remains:

```text
current_gate=HUMAN_GATE
execution_authorized=false
provider_requests=0
posts_allowed=0
```

No checklist proves present-day rights, evidence, identity, policy, capability, availability,
pricing, terms, revocation status or Provider acceptance. Even a later historically verified
Review Record with `PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY` authorizes only a separately reviewed
proposal-design step. It does not authorize access, upload, submit, retain, train, process,
generate, execute, publish, purchase or contact a Provider.
