# SDC Creative Sample Fresh Status Assessment Receipt Canonical Codec v3.0

## Purpose

Use this runbook only to encode one existing immutable Fresh Status Assessment Receipt V1 into
canonical JSON bytes or to parse explicitly supplied bounded canonical JSON bytes into that same
Receipt V1 contract.

This runbook authorizes no filesystem read or write, path operation, private-data operation,
historical closure verification, currentness finding, Provider call or execution. Every successful
result remains `HUMAN_GATE / NOT_AUTHORIZED`.

## Applicability gate

Use the codec only when:

- the input is already present in memory;
- encoding receives the exact
  `CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1` type; or
- parsing receives exact built-in `bytes` deliberately supplied by the caller;
- the caller needs only canonical document conversion or internal Receipt contract admission; and
- no claim of source trust, historical replay, current reality or authority will be made.

Do not use this codec with a path, directory, stream, file object, URL, clipboard discovery,
environment lookup, detached Slice 5 Result, partial Receipt, currentness request or Provider
operation.

## Module and exact public surface

The module is:

```text
sdc.real_asset_fresh_status_record_as_of_assessment_receipt_codec_v30
```

Its ordered `__all__` is exactly:

```text
FreshStatusRecordAsOfAssessmentReceiptCodecErrorCodeV1
RealAssetFreshStatusRecordAsOfAssessmentReceiptCodecV30Error
encode_fresh_status_record_as_of_assessment_receipt_v1_json
parse_fresh_status_record_as_of_assessment_receipt_v1_json
```

The module defines and exports no codec profile, JSON-depth constant, model, Result, Schema,
reader, writer, verifier, finalizer or CLI.

It reuses without re-exporting:

```text
Receipt canonical maximum = 65536 bytes
v3.0 JSON maximum depth = 32
```

## Exact APIs

Encoder:

```python
encode_fresh_status_record_as_of_assessment_receipt_v1_json(
    receipt: CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
) -> bytes
```

Parser:

```python
parse_fresh_status_record_as_of_assessment_receipt_v1_json(
    raw: bytes,
) -> CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
```

Both arguments are mandatory. Do not pass dicts, strings, bytearrays, memoryviews, paths, streams,
callbacks, upstream objects, chains, another `as_of`, replay Results, credentials or Runtime
handles.

## Canonical document checklist

Require all of the following simultaneously:

```text
exact built-in bytes
non-empty
length <= 65536 bytes
strict UTF-8
no BOM
Unicode NFC without normalization
one top-level JSON object
no duplicate key at any depth
no NaN or Infinity
JSON depth <= 32
sorted object keys recursively
two-space indentation
ensure_ascii=false
allow_nan=false
arrays retain frozen tuple order
exactly one final LF
no CRLF or trailing bytes
```

Do not trim, normalize, reorder, deduplicate, fill defaults, coerce types or repair a document. A
byte difference from the canonical Receipt document is an error.

## Encoding procedure

### 1. Supply one exact Receipt model

Call only:

```python
raw = encode_fresh_status_record_as_of_assessment_receipt_v1_json(receipt)
```

The operation does not accept or derive a path and does not write `raw` anywhere.

### 2. Strictly reconstruct the Receipt

Require the exact Receipt V1 class, dump its complete Python-mode projection and strictly rebuild
the model. Require model equality between the supplied and rebuilt values. Reject hidden/private
state, subclass substitution, model-construct bypass, invalid ID, invalid assessment digest,
limitation drift and zero-authority drift.

### 3. Encode canonical bytes

Encode the rebuilt Receipt using the frozen canonical rules. Require non-empty output no larger
than 65,536 bytes. Return only `bytes`.

Do not return a document hash, path, filename, delivery record, verified flag or authority result.

## Parsing procedure

### 1. Admit bounded bytes

Before decoding, require exact built-in `bytes`, non-empty input, length at most 65,536 and no BOM.

### 2. Parse strict JSON

Decode strict UTF-8. Reject malformed JSON, duplicate keys at every depth, non-finite numeric
constants and forbidden Unicode form. Require a top-level object and depth at most 32.

### 3. Admit the exact Receipt contract

Construct the Receipt V1 from JSON and strictly reconstruct it from its complete Python-mode
projection. This must execute the Receipt validators for:

- exact envelope, profile, source-profile and policy literals;
- Record, Request, Decision, closure and replay anchors;
- explicit `as_of` and half-open window state;
- `as_of_assessment_sha256`;
- `receipt_id` over every other Receipt field;
- all seven limitations;
- `HUMAN_GATE / NOT_AUTHORIZED`; and
- all false and zero authority values.

Schema shape or ID syntax alone is not sufficient.

### 4. Require exact canonical bytes

Render the parsed Receipt independently and require:

```text
raw == canonical_receipt_bytes(parsed_receipt)
```

Then return the newly parsed immutable Receipt. Do not add a timestamp, status, hash or verification
result.

## Contract admission versus historical verification

Encoding and parsing are document-codec operations only.

Parser success means:

> These exact bytes canonically encode an internally consistent Receipt V1.

It does not mean:

> The Receipt was freshly replayed against its complete upstream closure.

Only this existing Slice 6 operation performs the latter limited check:

```text
verify_fresh_status_record_as_of_assessment_receipt_closure_v1
```

That verifier requires the complete thirteen-value upstream closure, takes its one `as_of` from the
Receipt and freshly calls Slice 5 once. The codec accepts none of those upstream inputs and must
make zero Slice 5 and zero Slice 6 builder/verifier calls.

An attacker can produce an internally self-consistent model and recompute its IDs and digests.
Canonical parsing cannot establish its origin or match it to external upstream objects. Do not
label parser output trusted, verified, current, authentic or authorized.

## Fixed error order

The exact eight-code order is:

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

### Encoder mapping

| Condition | Required code |
| --- | --- |
| wrong type, invalid Receipt, hidden state, ID/digest/authority drift | `RECEIPT_INPUT_CONTRACT_INVALID` |
| impossible canonical serialization or bound failure after valid reconstruction | `INTERNAL_CODEC_INCONSISTENCY` |

### Parser mapping

| First failing stage | Required code |
| --- | --- |
| non-bytes, empty, oversize or BOM | `DOCUMENT_BYTES_CONTRACT_INVALID` |
| UTF-8, JSON, duplicate-key, non-finite or Unicode-form failure | `DOCUMENT_JSON_INVALID` |
| non-object root | `DOCUMENT_ROOT_INVALID` |
| depth greater than 32 | `DOCUMENT_DEPTH_EXCEEDED` |
| Receipt field, type, literal, ID, digest, limitation or authority failure | `DOCUMENT_RECEIPT_CONTRACT_INVALID` |
| valid model projection but non-canonical raw representation | `DOCUMENT_NOT_CANONICAL` |
| impossible internal failure after caller contracts were admitted | `INTERNAL_CODEC_INCONSISTENCY` |

The codec error exposes only `code` and a message. There are no Slice 2--5 nested replay codes.
Never parse error text to infer a different code.

Do not retry, repair, normalize, persist, roll back or quarantine after failure. Do not broadly
reclassify unrelated runtime, memory or process-interruption exceptions.

## Zero-authority confirmation

Every returned Receipt must retain:

```text
present_currentness_asserted=false
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
```

All seven limitation codes remain present in frozen order. Canonical bytes, a valid ID, a valid
assessment digest and successful parsing grant no authority.

## Synthetic test recipes

### Public surface and compatibility

- assert the exact four-name ordered `__all__`;
- inspect both one-argument signatures;
- prove no codec profile, codec model, Result, Schema or root re-export exists;
- require 68 registered models and all 68 committed Schema bytes unchanged.

### Encoder admission

- encode one synthetic valid Receipt and compare exact golden bytes;
- repeat encoding and compare bytes exactly;
- reject dict, subclass, other model and arbitrary object inputs;
- inject hidden/private state and require rejection;
- tamper ID, assessment digest, limitation, purpose, status and every authority field;
- require zero lower-layer calls and no output on failure.

### Parser byte/JSON admission

- test bytes versus string, bytearray, memoryview, path-like and stream-shaped objects;
- test empty, BOM, malformed UTF-8, limit and limit-plus-one;
- test malformed JSON, root and nested duplicate keys, NaN and Infinity;
- test object, array, string, number, boolean and null roots;
- test depth 32 and 33;
- test missing/unknown fields and bool/int/string coercion attempts.

### Canonical and Receipt admission

- test sorted keys, two-space indentation, Unicode escapes, whitespace, one LF, missing LF, CRLF and
  trailing data;
- independently verify stable-ID and assessment-digest tamper rejection;
- modify an assessment projection and recompute only `receipt_id`;
- preserve all limitations and zero-authority values;
- require `parse(encode(receipt)) == receipt`;
- require `encode(parse(raw)) == raw` for canonical bytes.

### Non-verification and static boundary

- parse a valid alternate synthetic Receipt without declaring it matched to another closure;
- separately demonstrate that only Slice 6 historical verification detects a wrong closure;
- monkeypatch lower APIs to prove codec call counts remain zero;
- exercise all eight error codes and competing-error precedence;
- propagate unrelated `RuntimeError`, `MemoryError` and process interruptions;
- AST-lock the production module against filesystem, path, stream, CLI, environment, implicit
  clock, external hash, persistence, network, Provider, credential, authority and execution APIs;
- run Slice 6 focused regressions and complete offline `make check` after exact scope checks.

All fixtures must be synthetic and in memory. Static tests may read approved tracked source and
Schema bytes only.

## Permitted success statements

Encoder:

> The supplied exact Receipt V1 model was strictly reconstructed and encoded as deterministic
> canonical JSON bytes within the frozen size limit.

Parser:

> The supplied exact bounded bytes are the canonical JSON representation of one internally
> consistent Receipt V1 model.

Do not add that the Receipt is trusted, authentic, historically verified, currently valid or
authorized.

## Prohibited operations

This runbook does not permit:

- reading, opening, statting, discovering or writing any path or directory;
- accepting a file object, stream, descriptor, HANDLE, URL or clipboard source;
- generating a file SHA, filename, delivery manifest or persistent output;
- calling a finalizer, rollback, quarantine or isolation operation;
- selecting latest, ordering Receipts, chaining history or renewing currentness;
- obtaining time from a clock, environment, file metadata, process, network or Provider;
- handling real evidence, identities, assets or private intake;
- network, Provider, Runtime, credential, Key, token, entitlement, database, queue or worker access;
- generation, execution, publication, purchase, contact, upload, retention or training; or
- commit, push, PR, merge, tag, release or deployment without separate explicit approval.

## Deferred trusted-local boundaries

Trusted-local readers, explicit path admission, directories, ACL/owner/link checks, CLI, create-new
writers and finalizers, external whole-document hashing, rollback, quarantine, Receipt history,
latest selection, currentness renewal, real data, network, Provider adapters, credentials,
entitlements and execution remain separately designed and separately approved work.

The codec's in-memory bytes are not advance approval for any of those operations.

## Verification handoff

Record only synthetic validation facts:

```text
codec module and exact four-name public surface
two API signatures
eight-code order and precedence
canonical UTF-8/LF and 65536/depth-32 results
Receipt ID and assessment-digest validation results
round-trip results
zero lower-layer invocation result
zero-authority result
Schema count and byte-preservation result
static forbidden-import/call result
focused regressions and offline make check result
```

Do not record a real path, identity, evidence source, asset status, Provider credential,
historical-verification claim, present-currentness claim or operational instruction.
