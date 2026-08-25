# SDC-ADR-037: Fresh Status Assessment Receipt Canonical Document Codec v3.0

- Status: Accepted
- Date: 2026-08-25
- Depends on: SDC-ADR-031 / Fresh Status Evidence v3.0 Slice 1
- Depends on: SDC-ADR-035 / Fresh Status Evidence Record As-Of Assessment v3.0 Slice 5
- Depends on: SDC-ADR-036 / Fresh Status Record As-Of Assessment Receipt v3.0 Slice 6
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: synthetic in-memory Receipt models and bounded canonical JSON bytes only

## Context

SDC-ADR-036 defines one immutable persistent Receipt contract and two pure in-memory operations:
one builder that freshly invokes Slice 5 and one historical closure verifier that freshly invokes
Slice 5 at the Receipt's exact `as_of`. It deliberately exposes no supported JSON/bytes codec,
filesystem reader, path, stream, writer or finalizer.

The committed Receipt Schema registers the document structure, but Schema admission alone does not
prove canonical bytes, stable-ID consistency, Slice 5 assessment-digest consistency or historical
closure replay. Conversely, parsing a structurally and internally consistent Receipt must not be
presented as evidence that Slice 5 ran or that the complete upstream closure was freshly verified.

Slice 7 closes only the canonical in-memory document-codec gap. It does not close the trusted-local
filesystem, persistence or operational verification gaps.

## Decision

Add one pure in-memory v3.0 codec module:

```text
src/sdc/real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30.py
```

The module serializes and parses only the existing:

```text
CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

It defines no new persistent contract, profile, policy, Result, envelope, digest or authority
state. It does not modify the Slice 6 module or its frozen public surface.

## Frozen compatibility boundary

Slice 7 must not change:

- the Receipt V1 model, fields, defaults, validators, stable-ID projection or canonical limit;
- the Slice 5 assessment digest domain or projection;
- the Slice 6 builder, historical verifier, errors, invocation count or provenance checks;
- any Slice 1 through Slice 6 public contract, profile, policy or Schema;
- any Frozen Pack through Use Scope Review contract;
- any trusted-local reader, writer, finalizer, rollback, quarantine or authority state; or
- any network, Provider, credential, entitlement or execution state.

`sdc.schemas.MODELS` remains exactly 68. The existing Receipt Schema remains the only Receipt
Schema. All 68 committed Schema paths and bytes remain unchanged. Slice 7 does not run Schema
generation.

## Exact public surface

The codec module's ordered `__all__` contains exactly these four names:

```text
FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1
RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error
encode_fresh_status_record_as_of_assessment_receipt_v1_json
parse_fresh_status_record_as_of_assessment_receipt_v1_json
```

There is no codec profile and no codec-specific JSON-depth constant. The module reuses, without
re-exporting:

- `FRESH_STATUS_RECORD_AS_OF_ASSESSMENT_RECEIPT_MAX_BYTES=65536`; and
- the existing v3.0 `FRESH_STATUS_JSON_MAX_DEPTH=32` policy constant.

There is no package-root re-export requirement.

## Exact APIs

The encoder is:

```python
encode_fresh_status_record_as_of_assessment_receipt_v1_json(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> bytes
```

The parser is:

```python
parse_fresh_status_record_as_of_assessment_receipt_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

Both parameters are required. The encoder accepts only the exact Receipt V1 model type. The parser
accepts only exact built-in `bytes`. Neither accepts a dict, string, `bytearray`, `memoryview`, path,
stream, file object, callback, upstream closure, chains, separate `as_of`, Slice 2--5 Result,
Provider handle, Runtime handle or credential.

## Canonical Receipt document

Slice 7 preserves the exact Slice 6 canonical document rules:

```text
UTF-8 without BOM
Unicode NFC; no normalization or repair
sort_keys=true recursively
indent=2
ensure_ascii=false
allow_nan=false
exactly one LF after the final closing brace
no CRLF
```

Arrays retain their frozen model order. The codec never sorts, deduplicates, truncates, fills,
merges or repairs array values. The maximum document size is inclusive and exactly 65,536 bytes.
The maximum JSON nesting depth is exactly 32, counting the top-level object as depth 1; entering an
object or array adds one and scalar members add zero.

## Encoder order

The encoder performs these phases in this exact order:

1. require the exact Receipt V1 model type;
2. obtain its complete Python-mode projection;
3. strictly reconstruct the complete Receipt V1 model;
4. require exact model equality between the supplied and reconstructed models, including absence
   of hidden or private non-canonical state;
5. serialize the reconstructed model using the frozen canonical rules;
6. require the canonical output to be non-empty and at most 65,536 bytes; and
7. return only the canonical `bytes`.

Strict Receipt reconstruction necessarily revalidates the complete zero-authority state,
`receipt_id` and `as_of_assessment_sha256`. The encoder does not call a private Slice 6 helper and
does not call Slice 5, the Slice 6 builder or the Slice 6 historical verifier.

The encoder does not return or persist a document SHA-256. Producing bytes is not permission to
write them to a file.

## Parser order

The parser performs these phases in this exact order:

1. require exact built-in `bytes`, non-empty input, length not greater than 65,536 bytes and no
   UTF-8 BOM;
2. decode strict UTF-8 and parse strict JSON while rejecting duplicate keys at any depth,
   NaN/Infinity and malformed JSON;
3. require one top-level JSON object;
4. compute the complete object/array nesting depth and require depth not greater than 32;
5. construct the exact Receipt V1 from the JSON document and strictly reconstruct it from its
   complete Python-mode projection;
6. require Receipt model equality across strict reconstruction;
7. independently render the parsed Receipt to canonical bytes and require exact byte equality with
   the supplied `raw`; and
8. return only the newly parsed immutable Receipt V1.

The parser never normalizes Unicode, line endings, whitespace, key order, missing defaults or
numeric/string/boolean types. If a repair would be necessary, parsing fails.

## ID and assessment-digest admission

Schema or regular-expression admission is insufficient. Encoder and parser strict reconstruction
must run the Receipt V1 validators that require:

```text
receipt_id == stable_id(
    "real_asset_fresh_status_record_as_of_assessment_receipt_v1",
    every Receipt field except receipt_id,
)
```

and independently recompute the existing Slice 5 `as_of_assessment_sha256` from the frozen
assessment projection and domain.

Slice 7 does not duplicate, replace or version either projection. It does not introduce a second
assessment digest or Receipt-document self-hash. A mismatch is a document/Receipt contract failure,
not a historical replay conclusion.

## Contract admission is not historical verification

Codec success proves only one of the following:

- encoder: the exact supplied Receipt V1 model was strictly reconstructed and rendered to its
  deterministic canonical bytes; or
- parser: the exact supplied bytes are the canonical representation of an internally consistent
  Receipt V1 model.

Codec success does not prove:

- that the Slice 6 builder or Slice 5 assessor ever ran;
- that the Receipt came from an authentic or trusted source;
- that the complete Frozen Pack through Use Scope Review closure matches the Receipt;
- that all explicit source chains were freshly replayed;
- that the Receipt's `as_of` came from an authentic clock or represents the present;
- that the recorded evidence is complete, true, current or legally effective;
- that no hidden or newer branch exists; or
- that any Provider, generation, execution, publication or other action is authorized.

Only the existing Slice 6
`verify_fresh_status_record_as_of_assessment_receipt_closure_v1` operation can make the limited
historical closure-consistency claim. It requires the complete thirteen-value closure and performs
one fresh public Slice 5 assessment. Slice 7 never calls it and never substitutes parsing for it.

The codec API and error messages must not use `verified`, `trusted`, `current`, `authorized` or
equivalent language as a success classification. No codec Result model or success flag exists.

## Fixed eight-stage error order

The exact ordered error-code literal is:

```text
RECEIPT_INPUT_CONTRACT_INVALID
DOCUMENT_BYTES_CONTRACT_INVALID
DOCUMENT_JSON_INVALID
DOCUMENT_ROOT_INVALID
DOCUMENT_DEPTH_EXCEEDED
DOCUMENT_RECEIPT_CONTRACT_INVALID
DOCUMENT_NOT_CANONICAL
INTERNAL_CODEC_INCONSISTENCY
```

The dedicated codec error exposes only its stable `code` and explanatory message. It contains no
Slice 2--5 replay code because no replay operation occurs.

Encoder precedence:

- wrong model type, failed strict Receipt reconstruction, hidden/private state, invalid stable ID,
  invalid assessment digest or other supplied Receipt inconsistency becomes
  `RECEIPT_INPUT_CONTRACT_INVALID`;
- failure to canonically serialize or bound a valid strictly reconstructed Receipt becomes
  `INTERNAL_CODEC_INCONSISTENCY`.

Parser precedence:

- wrong scalar type, empty bytes, oversize bytes or BOM becomes
  `DOCUMENT_BYTES_CONTRACT_INVALID` before decoding;
- invalid UTF-8, malformed JSON, duplicate keys, non-finite numbers or forbidden Unicode form
  becomes `DOCUMENT_JSON_INVALID`;
- a non-object JSON root becomes `DOCUMENT_ROOT_INVALID`;
- depth greater than 32 becomes `DOCUMENT_DEPTH_EXCEEDED`;
- missing/unknown fields, type coercion, literal drift, zero-authority drift, invalid ID, invalid
  assessment digest or any other Receipt model failure becomes
  `DOCUMENT_RECEIPT_CONTRACT_INVALID`;
- a fully valid Receipt projection whose raw spacing, key order, escapes or trailing bytes differ
  from the exact canonical document becomes `DOCUMENT_NOT_CANONICAL`; and
- an impossible deterministic codec failure after all relevant caller contracts were admitted
  becomes `INTERNAL_CODEC_INCONSISTENCY`.

No failure is retried, repaired, normalized, persisted, rolled back or quarantined. Unrelated
`RuntimeError`, `MemoryError`, `KeyboardInterrupt`, `SystemExit` and other non-domain process
failures are not broadly caught or reclassified.

## Zero-authority boundary

Every successfully encoded or parsed Receipt still contains the exact Slice 6 zero-authority
state, including:

```text
current_gate=HUMAN_GATE
provider_state=NOT_AUTHORIZED
generation_authorized=false
execution_authorized=false
publication_authorized=false
remote_processing_allowed=false
retention_allowed=false
training_allowed=false
publication_allowed=false
automated_execution_allowed=false
authorized_attempts=0
authorized_cost_cny=0
posts_allowed=0
provider_requests=0
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
present_currentness_asserted=false
```

All seven limitation codes remain present in frozen order. Encoding, parsing, canonical equality,
ID validity, digest validity or Schema compatibility changes none of these values or meanings.

## Pure-memory static boundary

The production codec module is limited to deterministic JSON parsing/serialization, Unicode-form
inspection, bounded byte/depth checks and strict Pydantic Receipt validation. It must not import or
call:

- filesystem, path, stream, descriptor, HANDLE, ACL, directory, glob or file metadata APIs;
- CLI, environment, subprocess, shell, import-discovery or dynamic-code APIs;
- implicit clock, wall-time, random, UUID or automatic `as_of` APIs;
- hashing for an external full-document digest;
- reader, writer, finalizer, rollback, quarantine, repair or persistence APIs;
- database, queue, worker, cache or ledger APIs;
- network, browser, HTTP, Provider or Runtime adapters;
- credential, Key, token, entitlement or authorization stores; or
- generation, execution, publication, purchase, contact, upload, retention or training APIs.

The codec has no import-time side effect, `__main__` branch, asynchronous operation or callback.

## Synthetic validation matrix

Slice 7 tests use synthetic in-memory Receipt models and byte strings only and cover at least:

### Public API and compatibility

- exact two signatures, required single parameters and exact four-name ordered `__all__`;
- no codec profile, Result model, root re-export or new exported limit;
- exactly 68 registered models and byte-identical preservation of all 68 Schemas;
- no modification of Slice 1--6 public APIs or behavior.

### Encoder

- exact canonical golden bytes and deterministic repeated encoding;
- exact model type rejection, including dict, subclass and non-Receipt models;
- strict reconstruction, stable-ID and assessment-digest rejection;
- hidden/private/non-projected state rejection;
- zero-authority and limitation preservation;
- non-empty and 65,536-byte output bound; and
- proof of zero Slice 5, Slice 6 builder and Slice 6 verifier calls.

### Parser bytes and JSON

- `bytes` versus str, bytearray, memoryview, path-like and stream-shaped inputs;
- empty, BOM, limit, limit-plus-one and malformed UTF-8 cases;
- malformed JSON, duplicate keys at the root and nested depths, NaN and Infinity;
- object root versus array, scalar and null roots;
- depth 32 and depth 33;
- missing and unknown fields, scalar coercion and tuple/order drift; and
- no truncation, sampling, normalization or repair.

### Receipt and canonical form

- valid ID/digest round trip;
- ID-only tampering, assessment-digest tampering and projection tampering with recomputed ID;
- every zero-authority literal, limitation tuple, purpose, status and present-currentness guard;
- key order, indentation, whitespace, escapes, LF, CRLF, extra trailing bytes and missing final LF;
- `parse(encode(receipt)) == receipt`;
- `encode(parse(raw)) == raw` for canonical raw bytes; and
- canonical rejection before any historical replay claim.

### Non-verification proof and static safety

- an internally consistent Receipt for another synthetic closure can encode and parse, while only a
  separate Slice 6 historical verifier call can reject it against the wrong closure;
- no Slice 5 assessor or Slice 6 builder/verifier invocation by either codec API;
- all eight error codes and their fixed competing-error precedence;
- no broad reclassification of unrelated runtime or process failures;
- AST rejection of filesystem, path, stream, CLI, environment, implicit clock, hash-output,
  persistence, network, Provider, credential, authority and execution surfaces; and
- complete offline `make check` after exact diff and Schema-byte checks.

## Permitted claims

After encoder success, the strongest permitted statement is:

> The exact supplied Receipt V1 model was strictly reconstructed and encoded as its deterministic
> canonical JSON bytes within the frozen byte limit.

After parser success, the strongest permitted statement is:

> The exact supplied bounded bytes are the canonical JSON representation of one internally
> consistent Receipt V1 model.

Neither is a historical verification, currentness statement, authenticity finding or authority.

## Deferred trusted-local and operational boundaries

The following remain separate future designs:

- trusted-local filesystem readers and explicit path admission;
- directory, owner, ACL, descriptor, HANDLE, link and reparse-point checks;
- CLI and explicit path checklists;
- create-new writers and finalizers;
- external whole-document SHA-256 and delivery metadata;
- rollback, quarantine, isolation and delivery-uncertainty handling;
- Receipt history chains, ordering, latest selection and currentness renewal;
- real-data operation;
- network and Provider adapters;
- credentials, Keys, tokens and entitlements; and
- generation, execution, publication or deployment.

Each requires a separate detailed design, synthetic validation and explicit approval. Canonical
bytes produced by Slice 7 are not advance approval to write, read or operationally use a file.

## Consequences

Positive consequences:

- the existing Receipt contract gains an exact bounded canonical round trip without contract or
  Schema duplication;
- stable-ID, assessment-digest, limitation and zero-authority validators run at the byte boundary;
- file/path authority remains absent; and
- historical verification remains visibly separate and cannot be silently replaced by parsing.

Costs and limits:

- callers still need a separately approved boundary to read or write bytes outside memory;
- parsing proves only internal contract consistency;
- no external document digest or provenance is produced; and
- full historical verification still requires every Slice 6 upstream input and a fresh Slice 5
  assessment.
