# SDC-ADR-029: Trusted-local closure path checklist v2.8

- **Status:** Accepted
- **Date:** 2026-08-21
- **ADR release:** 1.0
- **Operational boundary version:** 2.8.0
- **Bound finalizer version:** v2.7
- **Consumed contract Schema version:** none

## Context

SDC-ADR-028 introduced the trusted-local v2.7 Use Plan and Use Scope Review finalizers. Those
finalizers deliberately require every member of the selected physical closure as an explicit
command-line path. This keeps execution independent from discovery, directory scanning, mutable
aliases and hidden workflow state, but it also creates a repeated human task: a two-person team
must review and place 29, 32, 34 or 33 path arguments in a fixed order.

The safety boundary is correct and remains unchanged. The usability problem is the manual
preparation of those path lists. Recopying fourteen Pack media paths and the repository-external
closure can misplace one argument, omit an entry or silently target the wrong v2.7 command. A
helper may reduce that transcription cost only if it remains strictly upstream of human approval
and cannot become an execution adapter.

This ADR therefore defines a read-only checklist generator. It accepts one explicit, bounded seed
and one exact Pack Manifest reached from the explicit Pack root. It emits a deterministic JSON
checklist that names each v2.7 command-line path parameter. The checklist is evidence for manual
path review only. It is not accepted by a finalizer and is not an artifact, receipt, cache,
authorization or proof of current rights.

Acceptance of this ADR authorizes synthetic-only source and test implementation on the separately
approved v2.8 branch. It does not authorize access to a real Pack, Manifest, Use Plan, Review
Record, identity reference or authoring input. It also does not authorize commit, push, PR,
merge, deployment, Provider access or production execution.

## Decision

Add one independent operational module:

```text
sdc.real_asset_closure_path_checklist_v28
```

The module generates exactly four hard-coded checklist profiles for the immutable v2.7 finalizer
interfaces:

| Profile | Bound v2.7 operation class | Entries |
|---|---|---:|
| `USE_PLAN_29` | Use Plan inspection/finalization source closure | 29 |
| `REVIEW_REQUEST_32` | Maker Request preflight source closure | 32 |
| `REVIEW_INSTRUCTION_34` | Checker Instruction preflight or Record finalization source closure | 34 |
| `REVIEW_RECORD_VERIFICATION_33` | historical Review Record verification source closure | 33 |

There is no custom, reduced, inferred, latest/current, unknown-version or variable-length profile.
The generator is not a fifth finalizer operation and does not invoke any v2.7 operation.

The four fixed counts intentionally do not cover every same-count variation that might be
possible in the future. In particular, a new finalizer version, renamed parameter, reordered
parameter, added source or removed source requires a newly reviewed profile. V2.8 must fail closed
rather than dynamically adapting.

## Fixed source topology

All profiles begin with the same 29-entry Use Plan source closure:

```text
Pack root
Pack Manifest
fourteen media members in Pack Manifest order
Evidence
Reviewer A
Reviewer B
PairCheck
evidence retained record
evidence preparer reference
Reviewer A retained record
Reviewer B retained record
Qualification Request
Qualifier reference
Qualification Instruction
Qualification Decision
Rights Manifest
```

`REVIEW_REQUEST_32` adds the Use Plan, Maker identity reference and Maker authoring input.
`REVIEW_INSTRUCTION_34` additionally adds the Checker identity reference and Checker authoring
input. `REVIEW_RECORD_VERIFICATION_33` instead adds the Use Plan, both identity references and the
existing Review Record; it does not accept either authoring input.

Pack root is an explicit seed value. The Pack Manifest path is deterministically fixed to
`asset-pack.json` directly under that root. The fourteen media paths are derived, in exact
Manifest object order, by joining each accepted `object_path` to the admitted Pack root. Every
other path is supplied as one explicit seed field. The generator never supplies a missing value,
guesses a sibling, or searches a directory.

The terms `EXPLICIT` and `MANIFEST_DERIVED` describe only the origin of a path string in the
checklist. They do not describe the trustworthiness of the referenced bytes. Pack Manifest and
media entries use `MANIFEST_DERIVED`; Pack root and every external seed path use `EXPLICIT`.

## Hostile seed boundary

The seed is a bounded, explicitly selected ordinary local UTF-8 JSON file. The implementation
uses a fixed maximum and rejects an empty file, a UTF-8 BOM, malformed UTF-8, duplicate keys,
unknown keys, missing keys, type coercion, non-finite values and all profile-inapplicable fields.
LF and CRLF JSON whitespace are both accepted because seed bytes are transport, not a canonical
artifact. No seed ID or raw seed digest becomes an output authority field.

The seed contains exactly `schema_version`, `document_type`, `profile`,
`target_finalizer_module`, `target_finalizer_version`, `target_command` and one `explicit_paths`
object. `schema_version` is `1.0.0`, `document_type` is
`sdc.trusted-local-closure-path-checklist-seed`, and `target_finalizer_version` is `v2.7`. The
`explicit_paths` keys are the exact v2.7 CLI argument names, including leading `--`.
Module and version are equality guards against a fixed descriptor, not caller-controlled extension
points. A profile may accept only its fixed command whitelist and exact path-field set. It cannot
carry a caller-defined count, ordinal, source classification, execution flag or precomputed digest.

The seed path itself is not an entry in the generated checklist. Its raw bytes are not bound into
`path_list_sha256`. Semantically equivalent accepted seeds, including LF and CRLF representations,
produce the same result when their admitted path values are the same.

The implementation reads only the explicit seed and the exact Pack Manifest as file content.
Other selected targets may be inspected for safe path admission and identity, but their content
is not parsed, hashed or validated by this boundary.

## No discovery

The generator must not call glob, recursive glob, directory enumeration, tree walking or filename
search. It must not use `latest`, `current`, `newest`, modification time, creation time, lexical
sorting, a mutable pointer, an environment-selected directory or a default private root.

The exact Pack Manifest path is a fixed join from the explicit Pack root, not a discovered child.
The fourteen media paths are exact joins from the fourteen ordered Manifest `object_path` values,
not directory enumeration. The implementation rejects a Manifest with a different object count,
unsafe relative object path, traversal, absolute object path or a media path outside the admitted
Pack root.

## Path admission and rendering

Checklist paths use the same security posture as the bound v2.7 finalizers. Every seed and derived
target must be a fully qualified existing ordinary local path. Relative and empty paths,
UNC/network paths, device and extended-device namespaces, alternate data streams, symbolic links,
junctions, reparse points, non-anchor mounts, bind mounts, hard-linked files, non-regular files,
case-folded aliases and physical aliases fail closed as applicable to the path kind.

Admission inspects every existing lexical component without following redirection, resolves the
accepted path, compares lexical, resolved and opened identities where applicable, and rejects
ambiguity rather than silently repairing it. Pack root must be an ordinary directory. The
Manifest and all file entries must be ordinary single-link files. All fixed entries must remain
distinct under the same lexical, case-insensitive and physical-alias predicates used by v2.7.

Rendering happens only after admission:

- Windows paths use backslashes in the output;
- a trailing separator is removed from an ordinary path;
- a drive root such as `C:\` retains its required trailing separator;
- `normcase()` is not used and letter case is not proactively changed; and
- case-insensitive comparison may reject an alias but never rewrites the displayed value.

`path_list_sha256` is therefore computed from the admitted and rendered paths, not from the raw
strings in the seed. Slash choice and a harmless trailing separator cannot create two checklists
for the same admitted target, while a rejected alias is never normalized into acceptance.

This alignment does not mean a checklist pre-approves later finalizer admission. A finalizer must
independently reopen and revalidate every explicitly supplied path at execution time.

V2.8 does not reproduce finalizer-specific filename suffix, outcome-token or artifact-content
validation. A rendered path can therefore still fail the separately invoked v2.7 finalizer. The
checklist status means only that this bounded path-admission and mapping pass completed.

## Parameter-bound entries

Every output entry has exactly these fields:

```text
argument_name
occurrence
ordinal
path
source
```

`argument_name` is the exact existing v2.7 CLI parameter, including its leading `--`.
`ordinal` is the fixed zero-based position in the selected profile. `occurrence` is zero for a
non-repeated argument. The fourteen `--media-path` entries use occurrences `0` through `13` and
preserve Manifest order. `source` is exactly `EXPLICIT` or `MANIFEST_DERIVED`.

The output does not include a shell command, quoting instruction, response file, executable
`argv`, PowerShell array or finalizer-call object. Parameter names are displayed so a human can
place paths correctly in a separately approved operation; they are not an execution interface.

## Exact v2.7 version binding

Each profile is compiled from a hard-coded descriptor that binds:

```text
profile
target_finalizer_module
target_finalizer_version
target_command
entry_count
ordered argument names
repeated-argument occurrence counts
source classification
```

The only accepted finalizer version is `v2.7`. Seed `target_finalizer_module`,
`target_finalizer_version` and `target_command` values must equal one exact whitelisted
combination. The caller cannot request `latest`, a version range or a dynamically imported
finalizer. The generator does not introspect `argparse`, inspect source code or infer a new
interface at runtime.

If v2.7 is later replaced, if a parameter changes, or if a closure count or order changes, this
generator fails closed until a separately reviewed version adds a new descriptor. A v2.8
checklist never claims compatibility with an unknown finalizer.

## Deterministic checklist digest

`path_list_sha256` binds a canonical digest envelope containing only:

```text
profile
target_finalizer_module
target_finalizer_version
target_command
entry_count
ordered admitted entries
```

Each admitted entry contributes all five fields shown above. The envelope uses UTF-8 JSON with
`ensure_ascii=False`, two-space indentation, sorted keys and one final LF. It excludes the seed
pathname, raw seed bytes, seed line ending, filesystem timestamps, object identities, source
contents, the Pack Manifest digest, success status and authority-warning fields.

Binding version and target command prevents the same paths from being mistaken for a different operation.
Binding ordinal, argument and occurrence prevents a reordered path list from retaining the same
digest. The digest proves only that one rendered list was associated with one hard-coded
interface descriptor. It is not a content digest, complete-closure digest, right, identity proof,
receipt, bearer token or approval.

## Read-only and TOCTOU boundary

The generator writes no file. It performs no create, append, replace, permission change, ACL
change, cleanup, quarantine or rollback operation. It writes one success object to standard output
only.

The implementation captures the exact seed and Pack Manifest before generation and recaptures
both after all path admission and before success. Identity, size, exact-byte digest or relevant
metadata drift fails closed. A changed Pack root or derived path identity also fails admission.
There is no automatic retry and no cached snapshot accepted by a later operation.

The generator's TOCTOU checks protect the integrity of this one checklist calculation. They do
not bridge the time gap to a separately approved finalizer invocation. That later operation must
receive explicit paths and perform its own complete v2.7 replay.

## Output and zero-authority state

Success emits one compact, sorted-key UTF-8 JSON object followed by one LF. In addition to the
version binding, entries and `path_list_sha256`, every success includes:

```text
status=PATH_CHECKLIST_READY_FOR_HUMAN_REVIEW_ONLY
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
automated_execution_allowed=false
manual_confirmation_required=true
execution_authorized=false
current_gate=HUMAN_GATE
provider_requests=0
posts_allowed=0
```

The checklist never includes file contents, human-authored basis text, identity contents, stable
artifact IDs, authorization data, Provider credentials or a claim that the complete closure is
valid. Failures emit only a bounded generic fail-closed diagnostic and no private path.

No success status may say `ready to execute`, `validated closure`, `rights verified`,
`provider-ready`, `authorized` or an equivalent claim. `READY_FOR_HUMAN_REVIEW_ONLY` means only
that the path-list generator completed its own fixed structural and path-admission checks.

## Manual-only type and workflow separation

The checklist output is a terminal human-review aid. Project code must not provide:

- a v2.7 `--checklist`, `--seed` or checklist-file execution parameter;
- an API that converts checklist JSON to a finalizer path dataclass;
- a pipe from generator standard output into a finalizer;
- an orchestration function that generates and immediately executes;
- a receipt cache that treats `path_list_sha256` as a later execution guard; or
- a watcher, queue, worker or scheduled process that consumes a checklist.

Checklist models and v2.7 execution-path models remain type-separated. A human must review the
displayed parameter mapping and later explicitly submit every path under a separate, operation-
specific authorization. The finalizer ignores the checklist digest and independently validates
the complete physical closure.

Repository controls cannot prevent arbitrary external software from parsing JSON. The accepted
boundary is that this project exposes no supported automated consumption path and documents such
consumption as prohibited.

## Synthetic-only implementation

Implementation and tests use only generated temporary directories and synthetic bytes. They must
not inspect, hash or process a real Pack, Manifest, media object, Evidence, qualification record,
Rights Manifest, Use Plan, identity reference, authoring input or Review Record. They must not
read or modify repository `output/` or `tmp/`.

V2.8 adds no Pydantic production artifact, contract, Schema, migration, database, queue, ledger,
Key, Provider client, Runtime adapter or network dependency. It does not modify either v2.7
finalizer. All committed Schemas remain byte-identical.

## Required tests

The synthetic test suite must prove:

- the four profiles contain exactly 29, 32, 34 and 33 entries in fixed order;
- every entry has the exact v2.7 argument name, zero-based ordinal and occurrence;
- exactly fourteen media entries are derived in Manifest order;
- all other selected paths come from explicit applicable seed fields;
- LF and CRLF seeds with the same semantic values produce the same checklist and digest;
- BOM, duplicate, unknown, missing, coerced and profile-inapplicable seed fields fail closed;
- relative, network, device, link, reparse, hard-link, alias, duplicate and escaping paths fail;
- Windows slash and trailing-separator rendering is stable without proactive case conversion;
- seed or Manifest drift at every capture boundary fails closed;
- glob, recursive traversal and directory enumeration APIs are never called;
- unknown modules, commands, versions, counts, parameters and orders cannot be selected;
- output and `path_list_sha256` are deterministic and contain all zero-authority warnings;
- no shell command, executable `argv` or finalizer invocation is emitted;
- no file is created or modified and no clock, network or Provider API is used; and
- all existing committed Schemas remain unchanged.

## Alternatives rejected

### Let the finalizer discover paths

Rejected because it would weaken the v2.7 explicit-path boundary and make discovery part of an
authority-adjacent operation.

### Emit a ready-to-run command

Rejected because convenient quoting would turn a review aid into an execution transport and
encourage generation-to-execution without a fresh human decision.

### Let finalizers consume checklist JSON

Rejected because it would make the checklist a bearer object, collapse manual confirmation and
allow a stale path list to replace fresh explicit input.

### Scan the Pack object directory

Rejected because enumeration can include unbound files, reorder members and create a mutable
selection rule. Only ordered Manifest `object_path` values are accepted.

### Dynamically introspect finalizer arguments

Rejected because interface drift would silently change a checklist. Exact v2.7 descriptors must
be reviewed in source.

### Hash raw seed bytes

Rejected because formatting and LF/CRLF transport differences are irrelevant to the admitted path
mapping. The digest binds the canonical admitted envelope instead.

## Consequences

The two-person team gains a concise, deterministic and parameter-labelled review surface without
weakening the explicit execution interface. Media paths no longer require manual reconstruction,
and version/command binding makes a checklist visibly specific to one v2.7 operation.

The deliberate limitation is that the helper cannot complete an operation. It does not validate
source content, prove current rights, remember approval or authorize execution. Humans must still
review the list and explicitly supply every path to the selected finalizer. A future interface
change requires a new reviewed descriptor rather than automatic adaptation.
