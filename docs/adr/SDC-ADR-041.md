# SDC-ADR-041: Visual Prompt Profiles Compiler Integration

- Status: Accepted
- Date: 2026-08-27
- Depends on: SDC-ADR-039 / Deterministic Visual Prompt Profiles
- Projection dependency: SDC-ADR-040 / Visual Prompt Profiles Phase 1 Projection Manifest
- Baseline: `d548b0d5172f24499b60ff0fd83d0c719890d460`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: explicit local Creative Sample v2 input values, admitted first-party Profile text
  and deterministic local process evidence only; no source-input provenance or rights claim
- Network/spend boundary: zero network calls, zero credentials, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Context

SDC-ADR-039 and SDC-ADR-040 establish a deterministic offline visual Prompt profile catalog, exact
five-value resolution, immutable `VisualPromptProfileSnapshot` values, closed render-input
projections, byte-deterministic rendering and zero-authority `PromptRenderReceipt` evidence. The
Phase 1 implementation and its generated closure are present at the baseline above. All three
first-party Profiles are admitted only for offline rendering. No Profile, Catalog or Receipt grants
Provider, Runtime, Rights, Qualification, Retry, publication, training, spending or asset-promotion
authority.

`FIRST_PARTY_TEXT_REVIEWED` applies only to the authored Profile text. The Compiler can validate the
shape, identity and hash closure of a Creative Sample specification, but it cannot prove ownership,
license, privacy clearance or first-party provenance for its narrative, dialogue, visual directions,
asset descriptions or referenced media. This ADR records those values only as explicit local render
inputs and makes no broader source-content claim.

Phase 1 deliberately has no Compiler call site. Its types are internal frozen values rather than
released Pydantic contracts, and no compiled artifact currently closes over a Profile Snapshot,
render input, rendered Prompt or Prompt Receipt.

The existing Compiler has two released paths:

1. `compile_story` v1 copies `scene.narrative` into `PIR` and `GenerationJob` while deriving the
   current v1 identities.
2. `compile_creative_sample` v2 renders a fixed internal Prompt, includes that Prompt in
   `StoryboardShotV2` identity and then derives `PIRV2`, audio cue, `GenerationJob`, `JobGraph`,
   `AssemblyPlan` and `CreativeSampleCompilation` identities from that closure.

Replacing the existing v2 Prompt therefore changes every affected shot ID, job ID, idempotency key
and downstream compilation identity. It would also invalidate the committed Creative Sample Pilot
identity and other frozen regressions. Adding optional fields to an existing released contract would
change its committed JSON Schema and its canonical bytes. Neither action is compatible with SDC's
append-only contract discipline.

This ADR defines the first opt-in Compiler integration as a distinct immutable sidecar bound to the
existing released base compilation identity. It does not create a new byte-level digest for the
base compilation and does not claim that the sidecar independently hashes every base artifact byte.
It does not approve implementation while its status is `Proposed`. Acceptance will permit only a
separately reviewed offline BUILD conforming to the exact boundary below.

## Decision summary

The first Compiler-integration slice will:

- support only Creative Sample v2 source values;
- support only `asset_purpose=NARRATIVE_SHOT`;
- require one explicit human selection of one exact Profile for all shots in one exact source
  specification;
- resolve that selection by all five values against the committed generated static Catalog;
- call the existing `compile_creative_sample` function unchanged to produce the authoritative base
  compilation and its existing released identity;
- derive each `NarrativeShotPromptRenderInput` explicitly from the same source specification and
  its active approved asset versions;
- validate the derived values against the base compilation before rendering;
- produce exact Prompt bytes and one existing zero-authority `PromptRenderReceipt` per shot;
- return a new append-only immutable external sidecar without modifying the base compilation; and
- add exactly two top-level formal Pydantic contracts and two committed Schema files.

The slice will not connect its output to `GenerationJob`, `JobGraph`, Runtime, Provider, QC,
Candidate, Qualification, Rights Manifest execution, AssetVersion promotion or publication.

## Frozen compatibility boundary

This decision must not change the behavior, serialized value or deterministic identity of:

- `compile_story` or any v1 product;
- `compile_creative_sample` or its fixed internal Prompt renderer;
- `StoryInput`, NIR, PIR, `AudioMasterClock`, `JobGraph` or `AssemblyPlan`;
- `CreativeSampleSpec`, `NIRV2`, `PIRV2`, `StoryboardShotV2` or
  `CreativeSampleCompilation`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible` or
  `CharacterAssetBinding`;
- `GenerationJob`, its ID, its idempotency key or its fixed Attempt limit;
- the committed Creative Sample Pilot compilation ID;
- Temporal/PostgreSQL workflow ownership, Runtime state or persistence;
- Provider submit, inspect, download or cancel behavior;
- `SUBMISSION_UNKNOWN -> HUMAN_GATE`, `STOP-2` or any Retry decision;
- `qc.verify` technical PASS/FAIL or advisory semantic QC behavior;
- any of the 68 currently committed JSON Schema bytes; or
- any existing profile, catalog, input, receipt or generated-artifact digest domain.

The two new Schemas are appended. No existing Schema is renamed, regenerated under changed
semantics or removed.

## Compiler entrypoint and output shape

The future implementation will add one opt-in function in a new integration module. Its conceptual
signature is:

```python
compile_creative_sample_visual_prompts(
    spec: CreativeSampleSpec,
    request: CreativeSampleVisualPromptCompileRequestV1,
) -> tuple[CreativeSampleCompilation, CreativeSampleVisualPromptSidecarV1]
```

The exact public name may change only by amending this ADR before acceptance. The implementation
must not add a call to this function from the current client, workflow, worker, Provider or CLI.

The function performs these operations in order:

1. calculate the existing canonical Creative Sample specification SHA-256;
2. require it to equal `request.spec_sha256`;
3. call `compile_creative_sample(spec)` unchanged;
4. require the returned base compilation to carry the same specification SHA-256;
5. resolve the request's exact five-value selection against the committed static Catalog;
6. require the Snapshot purpose to be `NARRATIVE_SHOT`;
7. derive and cross-check one exact render input for every base storyboard shot;
8. render each Prompt with the existing Phase 1 renderer;
9. validate each Receipt against the exact Snapshot, input and Prompt bytes; and
10. construct and validate the immutable sidecar and its new semantic digest.

Any failure occurs before a sidecar value is returned. There is no partial output, fallback Profile,
best-effort shot omission or mutation of the base compilation.

## Formal input contract

The first new top-level model is
`CreativeSampleVisualPromptCompileRequestV1`. Its committed file is
`schemas/CreativeSampleVisualPromptCompileRequestV1.schema.json`.

Both new top-level models are immutable, strict Pydantic v2 contracts. They forbid unknown fields,
scalar coercion and post-construction mutation. Their inline nested definitions are equally closed;
no untyped `dict[str, object]` escape hatch is permitted.

It contains exactly these semantic fields:

```text
schema_version=1.0.0
request_purpose=COMPILE_OFFLINE_NARRATIVE_VISUAL_PROMPTS
base_compiler_contract=CREATIVE_SAMPLE_V2
selection_scope=ALL_NARRATIVE_SHOTS
spec_sha256
catalog_version
catalog_sha256
profile_id
profile_version
profile_sha256
selection_decision_kind=HUMAN_DECISION
selection_decision_ref
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
grants_rights=false
grants_qualification=false
grants_execution_authority=false
eligible_for_asset_promotion=false
replaces_rights_manifest=false
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
```

`spec_sha256`, `catalog_sha256` and `profile_sha256` are exact lowercase 64-hex values.
`catalog_version` and `profile_version` use the ADR-040 semantic-version codec. `profile_id` and
`selection_decision_ref` use the portable-ID codec. Unknown fields and scalar coercion fail closed.

The first slice accepts only `selection_decision_kind=HUMAN_DECISION`. An automated policy cannot
author this request merely because it is deterministic. Supporting an approved deterministic
selection policy requires a separate decision that defines its policy identity, inputs, evidence,
change control and authority boundary.

`selection_decision_kind` and `selection_decision_ref` are explicit caller-supplied assertions. The
Compiler validates their exact types and values but cannot prove that the referenced human decision
exists, is authentic or is sufficient for any purpose beyond selecting offline Profile text. They
grant no execution or rights authority.

One request selects one Profile for every narrative shot in one exact specification. Per-shot
selection, mixed Profile versions, fallback selection and mid-compilation replacement are not
supported.

## Exact five-value resolution

The Compiler boundary receives these five selection values explicitly:

```text
catalog_version
catalog_sha256
profile_id
profile_version
profile_sha256
```

It imports the generated `VISUAL_PROMPT_CATALOG` value from the package. It does not read the source
JSON, discover files, inspect the current working directory, consult an environment variable or
accept an arbitrary caller-supplied Catalog.

The existing Phase 1 resolver must establish all of the following:

- the supplied catalog version and digest match the generated Catalog;
- the Profile ID and version match exactly one entry;
- the supplied Profile digest matches the full semantic profile projection;
- the Profile purpose is `NARRATIVE_SHOT`;
- `offline_render_admission_status=HUMAN_REVIEWED_FOR_OFFLINE_RENDER`; and
- `profile_text_provenance_status=FIRST_PARTY_TEXT_REVIEWED`.

The resolver returns the existing resolver-only `VisualPromptProfileSnapshot`. The public Compiler
entrypoint never accepts a caller-constructed Snapshot. A Snapshot enters the compiled boundary only
through the exact sidecar projection below.

Catalog review fields such as `catalog_reviewer_ref` and `catalog_reviewed_at` never appear as
sidecar fields. `catalog_sha256` may bind them indirectly under the already accepted catalog
projection, but their literal values are not copied into a compiled artifact and grant no authority.

The Phase 1 loader validates only the generated Catalog shipped with the current package and does
not provide immutable repository history. This ADR adds no historical Catalog archive or discovery
mechanism. Re-verifying the Profile's historical offline-render admission therefore requires the
exact Catalog identified by `catalog_version + catalog_sha256` to remain available to the verifier.
If it is unavailable, a consumer may still recompute the embedded Profile, render-input, Prompt,
Receipt and sidecar integrity digests, but it must not claim to have re-proved the historical Catalog
admission decision. A future Catalog upgrade that requires durable cross-version re-admission must
first define an append-only historical Catalog registry or another separately reviewed mechanism.

## Narrative render-input derivation

For each `CreativeSampleShotSpec`, the integration derives one exact
`NarrativeShotPromptRenderInput` as follows:

| Render-input field | Authoritative source |
| --- | --- |
| `input_kind` | fixed `NARRATIVE_SHOT` |
| `narrative` | source shot `narrative` |
| `visual_direction` | source shot `visual_direction` |
| `action` | source shot `action` |
| `shot_size` | exact ADR-040 mapping from source shot enum |
| `camera_angle` | exact ADR-040 mapping from source shot enum |
| `camera_movement` | exact ADR-040 mapping from source shot enum |
| `emotion_by_character` | source shot map, emitted in ascending `character_id` order |
| `wardrobe_by_character` | source shot map, emitted in ascending `character_id` order |
| `props` | source shot's already canonical ordered tuple |
| `continuity_notes` | source shot `continuity_notes` |
| `dialogue` | exact referenced `DialogueLine` values in strictly ascending source ordinal |
| `character_asset_bindings` | each referenced Bible's active AssetVersion ID and content SHA-256 |
| `scene_asset_binding` | referenced scene Bible's active AssetVersion ID and content SHA-256 |

The integration must prove a one-to-one closure among source shot ordinal, compiled
`StoryboardShotV2`, scene Bible, character Bibles, dialogue lines and active asset versions. It must
reject:

- a missing, duplicate, inactive or cross-Bible asset version;
- a content digest not belonging to the exact active asset version;
- a character, scene or dialogue reference absent from the source specification;
- a compiled shot that does not match the source shot semantics and active binding IDs;
- a missing, duplicate, reordered or extra shot;
- a dialogue line outside the shot's declared references;
- a noncanonical mapping or tuple order; and
- any value outside the existing ADR-040 render-input codecs and bounds.

`CharacterAssetVersion.visual_description`, `SceneAssetVersion.visual_description`, Bible display
names and catalog display metadata do not enter the render input. Reusing any `visual_description`
would change Prompt semantics and requires a separately versioned input projection and new known
answers.

## Formal sidecar contract

The second new top-level model is `CreativeSampleVisualPromptSidecarV1`. Its committed file is
`schemas/CreativeSampleVisualPromptSidecarV1.schema.json`.

It contains exactly these top-level fields:

```text
schema_version=1.0.0
artifact_purpose=OFFLINE_VISUAL_PROMPT_COMPILATION_SIDECAR
base_compiler_contract=CREATIVE_SAMPLE_V2
selection_scope=ALL_NARRATIVE_SHOTS
base_compilation_id
spec_sha256
selection_decision_kind=HUMAN_DECISION
selection_decision_ref
profile_snapshot
shot_prompts
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
grants_rights=false
grants_qualification=false
grants_execution_authority=false
eligible_for_asset_promotion=false
replaces_rights_manifest=false
usage_restriction=MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION
sidecar_sha256
```

`profile_snapshot` follows the flattened explicit Snapshot projection frozen by ADR-040. Every
`VisualPromptProfile` projection key occurs exactly once, followed by the three derived
catalog-binding fields:

```text
asset_purpose
constraint_set
narrative_contexts
profile_id
profile_version
reference_asset_recipe
reference_asset_types
renderer_version
sections
shot_type
visual_style_id
profile_sha256
catalog_version
catalog_sha256
```

There is no nested `profile` wrapper and no duplication of `profile_id` or `profile_version` outside
the flattened semantic fields. The Snapshot contains no catalog-entry authority, review, display or
Provider-compatibility fields. `constraint_set` includes Prompt constraints and `qc_expectations`
because all three are Profile semantics. Inclusion in the Snapshot does not turn a QC expectation
into a Prompt line or QC fact.

`base_compilation_id` must equal the returned base compilation's existing released ID and use the
current `creative_sample_` plus 20 lowercase hexadecimal character form. `selection_scope` repeats
the request's fixed all-shot scope; it is not inferred from the array length alone.

`shot_prompts` contains one entry for every base `StoryboardShotV2`, in strictly ascending source
ordinal. Each entry has exactly these fields:

```text
source_shot_id
source_shot_ordinal
render_input
render_input_sha256
prompt
prompt_sha256
prompt_size_bytes
prompt_render_receipt
```

`render_input` is the complete ADR-040 `NarrativeShotPromptRenderInput` projection.
`render_input_sha256` is its existing domain-separated digest. `prompt` is the exact decoded UTF-8
Prompt text and must be NFC, use LF only, contain no BOM or trailing horizontal whitespace and end
with exactly one LF. Re-encoding `prompt` as UTF-8 must reproduce the exact rendered Prompt bytes.
`prompt_sha256` is the raw SHA-256 of those bytes and `prompt_size_bytes` is their exact length.

`shot_prompts` contains exactly 8..12 entries because that is the released Creative Sample v2 shot
bound. `source_shot_id` must equal the corresponding base shot ID and use the current
`storyboard_shot_v2_` plus 20 lowercase hexadecimal character form. `source_shot_ordinal` is an
exact integer in `0..11`; the admitted array uses contiguous values beginning at zero.
`prompt_size_bytes` is an exact integer in `1..65536` and must equal the UTF-8 byte length.

`prompt_render_receipt` is the complete existing ADR-039/040 Receipt document projection, including
`prompt_render_receipt_sha256` and every direct zero-authority field. It is produced by the existing
renderer, not accepted from the request. The enclosing entry must reject any mismatch among its
Snapshot, render input, Prompt, repeated digests, byte size and Receipt.

The sidecar is an external companion to the base compilation. It neither embeds nor replaces the
base `CreativeSampleCompilation`. A consumer must possess both exact values and verify
`base_compilation_id + spec_sha256` before treating the sidecar as process evidence.

That pair binds the existing released base identity and the full existing specification digest. It
is not a raw-byte or new domain-separated digest of the complete base compilation. A consumer must
also run the existing base-contract validators; the sidecar alone cannot prove the exact serialized
base bytes. Adding a full base-compilation digest later requires a separately frozen projection and
unique domain.

`selection_decision_ref` records the caller's reference to the asserted human selection input only.
It is not proof of that review, the Catalog reviewer, a Rights reviewer, a Provider authorization or
an execution approval. The fixed
`retention_allowed=false` value denies any remote or Provider retention authority; it does not turn
the repository-local immutable sidecar itself into an external retention operation.

The sidecar contains local narrative and dialogue Prompt text. Its local persistence does not prove
that the text is nonsensitive, first-party or cleared for any later remote processing, retention or
publication.

The nested Snapshot and shot-entry objects are closed inline definitions in the sidecar Schema.
They do not create additional top-level Schema files or `MODELS` entries in this slice.

## Sidecar identity

This ADR reserves and, if accepted, freezes exactly one new semantic digest domain:

```python
b"sdc:visual-prompt-compiler-sidecar:v1\0"
```

`sidecar_sha256` is:

```text
lowercase_hex_sha256(
  b"sdc:visual-prompt-compiler-sidecar:v1\0"
  || canonical_compact_json(every exact sidecar field except sidecar_sha256)
)
```

The canonical codec is the accepted ADR-039/040 codec: strict NFC strings, UTF-8,
`allow_nan=false`, `ensure_ascii=false`, compact separators, lexicographically sorted object keys,
semantic array order, no BOM, no CR, no insignificant whitespace and no terminal LF.

The new digest directly closes over:

- the existing released base compilation identity and exact specification digest;
- the human selection-decision reference;
- the complete admitted Profile Snapshot;
- every ordered source shot identity;
- every complete render input and its existing semantic digest;
- every exact Prompt text, raw byte digest and byte length;
- every complete Prompt Receipt; and
- every direct sidecar zero-authority field.

It excludes only itself. No optional short ID is required. If a later presentation layer introduces
a short handle, the full `sidecar_sha256` remains authoritative and the handle must bind it.

The existing Compiler `stable_id` helper is not a substitute for this digest. No existing Phase 1
domain is reused or extended.

## Contract and Schema Registry impact

Acceptance permits exactly these two append-only formal models:

1. `CreativeSampleVisualPromptCompileRequestV1`
2. `CreativeSampleVisualPromptSidecarV1`

They are appended to `sdc.schemas.MODELS` in that order. The Registry count changes deliberately
from 68 to 70. The set of committed Schema files changes from 68 to 70 by adding only the two files
named above.

Every currently committed Schema byte remains unchanged. Existing historical digest maps continue
to cover the exact files they cover today. The implementation must add a new baseline asserting all
68 pre-integration Schema byte digests and must update the current Registry count assertion to the
accepted count of 70 without regenerating an old Schema.

An internal-only helper that leaves the Registry at 68 is not a conforming implementation of this
ADR because it would not provide a released, persistable and integrity-checkable Compiler boundary.
Historical Catalog admission remains conditional on availability of the exact Catalog as specified
above; `persistable` does not imply an immutable Catalog-history claim.

## Prompt, QC, Provider and Rights separation

The following meanings remain disjoint:

| Information | Permitted effect | Prohibited interpretation |
| --- | --- | --- |
| Positive Prompt constraints | Exact requested Prompt text | Proof the request was satisfied |
| Negative Prompt constraints | Exact avoidance request text | QC observation or failure fact |
| `qc_expectations` | Snapshot-carried future evaluator guidance | Prompt text, QC PASS/FAIL, Retry or promotion decision |
| Provider compatibility observation | Catalog-only syntax observation | Provider selection, capability, entitlement or authority |
| Profile admission | Offline deterministic rendering | Provider, Runtime or Candidate authority |
| Prompt Receipt | Exact process binding | Rights proof, approval conclusion or Rights Manifest replacement |
| Creative Sample source text | Explicit local render input | First-party provenance, privacy clearance or commercial rights |
| Active AssetVersion binding | Exact imported approved content identity | Permission to create or promote generated media |
| Rights Manifest | Separately reviewed rights closure | Provider capability or automatic publication authority |

Provider compatibility observations do not appear in the Snapshot or sidecar. They may affect the
already accepted Catalog digest but cannot select a Provider, model, syntax fallback or Runtime
route.

The sidecar must not call or modify `qc.verify`. A Profile constraint or expectation cannot reserve
an Attempt, initiate Retry, produce `STOP-2`, qualify an asset or authorize publication.

Neither the request nor the sidecar is a Rights Manifest. Both directly state
`replaces_rights_manifest=false` and `grants_rights=false`.

## Runtime and execution isolation

The new types are offline Compiler evidence and must be structurally and operationally isolated
from execution:

- the existing `compile_creative_sample` call creates its unchanged base `GenerationJob` and
  `JobGraph` values exactly as before;
- no additional or Profile-derived `GenerationJob` or `JobGraph` is created or substituted;
- the existing Job Prompt remains the existing v2 Prompt;
- no sidecar field is a Provider request, task ID, idempotency key or retry counter;
- no Temporal workflow accepts the sidecar as input;
- no client, worker or Runtime module imports the integration module;
- no Provider adapter accepts the sidecar or its Prompt;
- no credential, environment variable, filesystem discovery, clock, random value or network call is
  read during compilation;
- no media is created, uploaded, downloaded, retained or published; and
- every direct authority/cost/count field remains its frozen false/zero value.

The existence, validity or successful rendering of a sidecar cannot change any authority field.
The base `GenerationJob.max_attempts=2` remains its existing structural retry ceiling;
`authorized_attempts=0` on the request, sidecar and Receipts grants no Attempt and cannot activate
that ceiling.

## Generated-reference Candidate provenance boundary

This slice does not compile the `CHARACTER_REFERENCE_ASSET` or `SCENE_REFERENCE_ASSET` Profiles and
does not create a generated-reference Candidate.

The current `CharacterAssetVersion` and `SceneAssetVersion` contracts truthfully describe only
`IMPORTED_APPROVED_MEDIA`. Generated media cannot be relabeled under that literal, even after a
download, human review or re-import operation. This is a permanent fail-closed rule for those
contract versions.

A later generated-Candidate path requires its own provenance and Qualification ADR. That ADR must
define Candidate identity, generation/Provider Attempt evidence, Profile and Receipt binding,
content hashes, human Qualification, Rights Manifest integration, retention/privacy, revocation and
promotion semantics. This ADR grants no advance approval for it.

Offline rendering of a reference-profile Prompt is not itself Candidate creation, but the current
Compiler source does not define an unambiguous character- or scene-reference authoring input. Such
rendering is therefore deferred rather than inferred from `visual_description` or arbitrary shot
text.

## Multiple reference-role boundary

This slice preserves exactly one active primary AssetVersion per character and scene Bible. It does
not create a typed role sidecar, add active AssetVersions or bind multiple role-specific images to a
Provider request.

Reference role literals and recipes remain descriptive Profile semantics only. If a future Provider
route needs simultaneous role-specific images, a separate ADR must define:

- pre-promotion Candidate evidence and post-promotion AssetVersion-bound lifecycle states;
- an append-only V2 asset binding or Provider input-material contract;
- exact role cardinality and canonical order;
- media count, type and size limits;
- persistence and Rights closure;
- Provider request and idempotency impact; and
- zero-authority behavior before all required gates close.

Existing AssetVersion contracts must not be extended or reinterpreted in place.

The generated-reference provenance issue blocks Candidate promotion. The multiple-role issue blocks
multi-reference Provider execution. Neither blocks the narrative-only offline sidecar defined by
this ADR.

## Failure behavior

The integration fails closed for at least:

- a request specification digest mismatch;
- any Profile or Catalog identity mismatch;
- an inadmissible, retired, draft, rights-review-required or prohibited-external-content Profile;
- a Profile purpose other than `NARRATIVE_SHOT`;
- a request covering fewer or more than all base storyboard shots;
- any source/base compilation semantic mismatch;
- an inactive, missing, duplicate or cross-Bible asset binding;
- any render-input projection or ordering violation;
- any Prompt byte, raw digest or size mismatch;
- any Receipt field or semantic digest mismatch;
- any non-false/non-zero authority value;
- an unknown field, coercible scalar, noncanonical string or unrecognized enum; and
- any attempt to send the sidecar to an execution path.

Failure returns no sidecar and performs no external action. It never falls back to the existing
Prompt as if Profile rendering had succeeded; the unchanged base compilation remains a separately
returned product only after the caller has explicitly invoked this opt-in function.

## Validation and implementation gates

No implementation begins until this ADR is Accepted. A conforming BUILD must then pass a separate
review and prove at least:

1. current `main`, baseline and ADR dependency verification before implementation;
2. exact request and sidecar field sets, constants, codecs, bounds and unknown-field rejection;
3. exact five-value static-Catalog resolution with no default, latest, fallback or Agent selection;
4. one Profile for all narrative shots and rejection of per-shot or mixed selection;
5. complete source-to-base-to-render-input asset/content-hash and dialogue closure;
6. exact flattened Snapshot and Receipt projection binding;
7. independent calculation of the literal new sidecar domain and digest;
8. mutation of every sidecar semantic field changing `sidecar_sha256`;
9. byte-identical Prompt, input digest and Receipt results across supported Windows and Linux hosts;
10. unchanged v1 Compiler canonical output hash;
11. unchanged Creative Sample v2 output, Prompt, IDs and committed Pilot compilation ID;
12. byte-for-byte equality of all 68 pre-integration committed Schemas;
13. exactly two added Schema files and `sdc.schemas.MODELS` exactly 70;
14. sidecar structural rejection by Runtime, Provider and JobGraph paths;
15. proof that QC expectations do not enter Prompt bytes or QC decisions;
16. proof that Catalog/Receipt/sidecar validity grants no Rights, Qualification or execution;
17. proof that no Candidate, AssetVersion, role sidecar or promotion result is created;
18. static and runtime denial of network, credential, environment, clock, randomness and dynamic
    import inputs;
19. proof that missing historical Catalog bytes prevent a renewed admission claim without
    preventing honest integrity-only verification; and
20. complete offline `make check` success with no paid or remote service call.

The implementation review must include complete human-readable known-answer packets for at least:

- one basic narrative shot;
- one Unicode/NFC narrative shot;
- one no-character/no-dialogue narrative shot; and
- one multi-character shot with ordered dialogue and active asset content hashes.

An implementation PR must remain Draft until those packets, the two new Schemas and every changed
golden identity have received explicit human review. Acceptance of this ADR is not approval of an
implementation PR.

## Rejected alternatives

The following alternatives are rejected:

- replacing `_creative_prompt` in place;
- changing `StoryboardShotV2.prompt` semantics without a new contract version;
- inserting Profile Prompt bytes into the existing `GenerationJob`;
- adding optional Profile, Snapshot or Receipt fields to a released contract;
- treating `stable_id` as the sidecar semantic digest;
- relying on incidental dataclass or Pydantic serialization for a hash projection;
- caller-supplied Catalogs or caller-constructed Snapshots;
- per-shot Profile selection in the first integration slice;
- deriving reference prompts from `AssetVersion.visual_description`;
- including Catalog reviewer metadata in the compiled sidecar;
- treating Provider compatibility as Provider selection or authority;
- embedding QC expectations in Prompt bytes;
- creating a Candidate, reference image, role sidecar or new AssetVersion;
- adding a Runtime/Provider consumer for the sidecar; and
- keeping `MODELS` at 68 while claiming a formal Compiler artifact contract exists.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | In-place Prompt replacement changes the complete v2 identity chain | Preserve the base Compiler and use an external sidecar |
| Blocking | Ambiguous Profile selection changes outputs nondeterministically | Exact five-value human request, one Profile per compilation, no fallback |
| Blocking | Caller-asserted bindings do not match active Bible assets | Derive and cross-check exact IDs plus content SHA-256 values |
| Blocking for later Candidate work | Generated media cannot truthfully use current provenance | Keep generation and promotion out; require separate provenance/Qualification ADR |
| Blocking for later Provider work | Multiple reference roles lack an approved binding lifecycle | Keep roles descriptive; require append-only Provider-input ADR |
| Important | Sidecar mistaken for a runnable JobGraph or authorization | Distinct type, direct zero-authority fields and no Runtime import/call site |
| Important | Existing and Profile Prompt values become competing truths | Name sidecar Prompt as offline evidence; current v2 Prompt remains authoritative for current jobs |
| Important | Raw and semantic hashes are mixed | Reuse existing domains exactly and add one unique sidecar domain |
| Important | Catalog review metadata leaks into compiled artifacts | Carry only Snapshot semantics and Catalog identity, never literal reviewer fields |
| Important | New Schema generation drifts old contract bytes | Append two Schemas and hash all 68 pre-integration files |
| Minor | Operator labels or display grouping lag the new artifact | Keep presentation outside semantic projections and defer |

## Non-goals

This ADR does not approve or specify:

- Profile-driven v1 compilation;
- Character or scene reference Prompt compilation;
- generated image or video Candidates;
- Runtime or Provider execution;
- Provider/model selection or fallback;
- credentials, network, remote processing, retention or spending;
- Retry, Creative Attempt 2 or recovery logic;
- automated or semantic QC decisions;
- Qualification or AssetVersion promotion;
- Rights Manifest creation, finalization or execution;
- publication, posting or training;
- multiple reference-role media binding;
- per-shot mixed Profile selection;
- automated deterministic selection policies; or
- migration of any existing compiled artifact.

## Permitted claims and explicit non-proofs

After a conforming implementation is separately approved, SDC may claim only that one exact human
selection assertion, one exact compile-time-admitted narrative Profile Snapshot and one exact local
Creative Sample v2 input deterministically produced an immutable offline Prompt sidecar and process
Receipts while preserving the existing released base compilation identity. Renewed historical
admission verification remains conditional on availability of the exact Catalog.

This cannot prove or grant:

- Prompt quality or Provider suitability;
- satisfaction of a positive or negative constraint;
- QC PASS, retry eligibility or recovery authority;
- Candidate provenance or generated-output rights;
- ownership, license, privacy clearance or first-party provenance of source narrative, dialogue,
  directions or referenced media;
- Qualification or AssetVersion status;
- Rights Manifest closure or commercial-use permission;
- Provider capability, entitlement, credential or execution authority;
- retention, remote processing, training, spending or publication permission; or
- compatibility of a future executable Profile Prompt with the current Runtime identity chain.

## Consequences

Positive consequences:

- existing v1 and Creative Sample v2 products remain byte- and identity-compatible;
- the human-selection assertion becomes an explicit Compiler input;
- Snapshot, render input, exact Prompt bytes and Receipt form one deterministic integrity closure;
- the sidecar states honestly that Catalog re-admission requires the exact historical Catalog;
- active asset content hashes become explicit Prompt inputs rather than implicit context;
- zero authority is carried directly at every new formal boundary; and
- later executable Prompt work cannot silently inherit approval from this offline slice.

Costs:

- the Schema Registry intentionally grows from 68 to 70;
- the sidecar duplicates some information already bound by the base compilation and Receipt;
- all narrative shots initially use one Profile version;
- reference-profile compilation remains deferred; and
- any sidecar field or hash-projection change requires an explicit version/domain change and new
  known answers.

Until this ADR is Accepted and a separate implementation passes its complete review, SDC must
continue to claim that no Visual Prompt Profiles Compiler integration, formal request contract,
formal sidecar contract or sidecar digest exists.
