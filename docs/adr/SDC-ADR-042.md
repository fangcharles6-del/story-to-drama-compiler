# SDC-ADR-042: Character and Scene Reference Prompt Compiler Input Boundary

- Status: Accepted
- Date: 2026-08-27
- Depends on: SDC-ADR-039 / Deterministic Visual Prompt Profiles
- Projection dependency: SDC-ADR-040 / Visual Prompt Profiles Phase 1 Projection Manifest
- Compiler-boundary dependency: SDC-ADR-041 / Visual Prompt Profiles Compiler Integration
- Baseline: `ad807c9d98332da042dc413b221f1ebe0841d4fc`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: one supplied Creative Sample Character or Scene Bible value, caller-supplied local
  reference directions accompanied by an unauthenticated human-authoring assertion, one reference
  Profile whose authored Profile text has the accepted first-party-text status and deterministic
  local process evidence only; no proof of source authorship, bound-media rights or privacy clearance
- Network/spend boundary: zero network calls, zero credentials, zero Provider requests, zero
  authorized Attempts and zero authorized cost

## Context

SDC-ADR-039 and SDC-ADR-040 establish deterministic offline visual Prompt Profiles for narrative
shots, character reference assets and scene reference assets. They freeze exact five-value Profile
resolution, the resolver-only `VisualPromptProfileSnapshot`, three closed render-input variants,
byte-deterministic Prompt rendering and a zero-authority `PromptRenderReceipt`.

SDC-ADR-041 adds an opt-in Compiler sidecar for only `asset_purpose=NARRATIVE_SHOT`. It deliberately
does not compile `CHARACTER_REFERENCE_ASSET` or `SCENE_REFERENCE_ASSET` because the released Creative
Sample v2 contracts do not contain an unambiguous authoring source for those Prompts. Inferring a
reference Prompt from a Bible or AssetVersion `visual_description`, display name, arbitrary shot,
dialogue line or Profile recipe would silently invent a new source projection.

The accepted ADR-041 implementation is present at the baseline above. The Schema Registry contains
exactly 70 models: the pre-ADR-041 68 models plus its request and narrative sidecar. Existing v1,
Creative Sample v2 and narrative Prompt sidecar outputs have released deterministic identities and
committed Schema bytes.

The Phase 1 renderer already accepts these internal frozen values:

- `CharacterReferencePromptRenderInput`, which carries exactly one character asset binding; and
- `SceneReferencePromptRenderInput`, which carries exactly one scene asset binding.

Those values can render one complete reference-sheet Prompt from one admitted reference Profile.
They do not independently prove that a binding is active, imported or present in a Bible. They are
not formal Compiler input or artifact contracts. No released Compiler function currently defines
where the authoring text comes from, how it is closed against a Bible-declared active imported
AssetVersion, how the result is identified or what a verifier may claim.

This ADR defines that missing input boundary. Acceptance records the architecture only and
authorizes no implementation, formal Contract, Schema, registry change, digest use, generation,
Candidate, Qualification, Provider input or Runtime connection. A separately approved and reviewed
offline BUILD is still required to implement the exact boundary below.

## Decision summary

The first reference-Prompt Compiler slice will:

- accept exactly one released `CharacterBible` or exactly one released `SceneBible` per call;
- accept all story-specific Prompt authoring text through one explicit closed caller-supplied source
  variant carrying an unauthenticated human-authoring assertion rather than deriving that text from
  the Bible;
- require the source variant, requested asset purpose and exact Bible type to agree;
- derive exactly one Bible-declared active primary asset binding and require it to match the
  request's expected version ID and content digest;
- require one exact human selection of one exact matching reference Profile by all five values;
- resolve that Profile only from the committed generated static Catalog;
- render exactly one composite reference-sheet Prompt with the existing Phase 1 renderer;
- return one independent immutable offline Prompt Artifact containing the complete source,
  Snapshot, render input, exact Prompt, Receipt and integrity closure; and
- only after a separate BUILD is approved, add exactly two top-level formal Pydantic contracts and
  two committed Schema files.

The first slice will not:

- call or modify `compile_creative_sample`;
- accept a complete `CreativeSampleSpec` or compile every Bible in a specification;
- create or alter a `CreativeSampleCompilation`, `GenerationJob`, `JobGraph` or Provider request;
- treat Profile recipe roles as separate Prompt, image, Candidate or AssetVersion outputs; or
- connect the Artifact to Runtime, Provider, Retry, QC automation, Rights execution,
  Qualification, AssetVersion promotion, publication, retention or training.

## Acceptance record and implementation gate

Acceptance explicitly confirms:

1. the one-Bible/one-composite-Prompt scope;
2. the explicit human-authoring source projection and its non-proof semantics;
3. exactly two future top-level Contracts and the Registry change from 70 to 72; and
4. the independent Artifact projection and digest domain.

Acceptance is not implementation approval. A later BUILD must start from a newly verified
authoritative `main`, remain isolated and pass every gate below before its Draft PR can be approved.

## Frozen compatibility boundary

This decision and any conforming future implementation must not change the behavior, serialized
value, Schema or deterministic identity of:

- `compile_story` or any v1 product;
- `compile_creative_sample` or any Creative Sample v2 product;
- `CreativeSampleSpec`, `CreativeSampleCompilation`, `NIRV2`, `PIRV2`, `StoryboardShotV2`,
  `GenerationJob`, `JobGraph` or `AssemblyPlan`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible` or
  `CharacterAssetBinding`;
- `CreativeSampleVisualPromptCompileRequestV1`,
  `CreativeSampleVisualPromptSidecarV1` or the ADR-041 narrative sidecar digest;
- any v1 or Creative Sample v2 Prompt, ID, idempotency key or frozen regression byte;
- the committed Creative Sample Pilot compilation identity;
- Temporal/PostgreSQL workflow ownership, Runtime state or persistence;
- Provider submit, inspect, download or cancel behavior;
- `SUBMISSION_UNKNOWN -> HUMAN_GATE`, `STOP-2` or any Retry decision;
- `qc.verify` technical PASS/FAIL or advisory semantic QC behavior;
- any existing Profile, Catalog, render-input, Prompt Receipt, Catalog Receipt or narrative sidecar
  digest domain; or
- any of the 70 committed JSON Schema bytes and their first 70 `sdc.schemas.MODELS` entries.

A future conforming BUILD appends two Schemas. It must not rename, remove or regenerate an existing
Schema under changed semantics.

## Single-subject Compiler boundary

The future implementation will add one opt-in function in the new isolated module
`src/sdc/visual_reference_prompt_compiler.py`, imported as
`sdc.visual_reference_prompt_compiler`:

```python
compile_creative_sample_reference_visual_prompt(
    subject: CharacterBible | SceneBible,
    request: CreativeSampleReferenceVisualPromptCompileRequestV1,
) -> CreativeSampleReferenceVisualPromptArtifactV1
```

The entrypoint processes exactly one subject and returns exactly one Artifact. The future module's
complete public export surface is frozen to:

```text
CreativeSampleReferenceVisualPromptCompileRequestV1
CreativeSampleReferenceVisualPromptArtifactV1
VisualReferencePromptCompilerError
VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN
compile_creative_sample_reference_visual_prompt
creative_sample_reference_visual_prompt_artifact_projection
creative_sample_reference_visual_prompt_artifact_sha256
```

The public Artifact helper contracts are frozen to:

```python
creative_sample_reference_visual_prompt_artifact_projection(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> dict[str, object]

creative_sample_reference_visual_prompt_artifact_sha256(
    value: CreativeSampleReferenceVisualPromptArtifactV1,
) -> str
```

Both helpers accept only an exact `CreativeSampleReferenceVisualPromptArtifactV1` instance, reject
subclasses and fully strict-revalidate the complete value. Revalidation rejects forged construction
or `model_copy` values and unknown, cyclic or dynamically typed nested values. Integrity validation
locally re-renders from the embedded reference Snapshot and render input, then requires exact Prompt
and Prompt Receipt equality. It performs no Catalog, Bible, filesystem, environment or network
lookup and no authority action.

The projection helper returns the explicit closed semantic projection of every Artifact field except
`artifact_sha256`. The hash helper hashes exactly that projection under
`VISUAL_REFERENCE_PROMPT_COMPILER_ARTIFACT_SHA256_DOMAIN`. Neither helper derives its projection
from incidental Pydantic, dataclass or `__dict__` serialization. On any failure, both helpers raise
`VisualReferencePromptCompilerError`, preserve the original exception as the cause and return no
partial value or sentinel. Exact human-readable error text is not a compatibility interface.

Adding or renaming a public export requires an explicit ADR amendment and review before
implementation. The module must not be imported or called by the current client, CLI, workflow,
worker, Runtime, Provider or QC modules.

The function performs these operations in order:

1. require one exact released `CharacterBible` or `SceneBible` instance and fully revalidate its
   complete serialized value under its released contract;
2. validate the exact future request and its zero-authority constants;
3. close the request's asset purpose, source tag, subject ID and exact Bible type;
4. locate exactly one Bible-declared active AssetVersion, validate its subject binding, identity,
   media type, released provenance literal and content digest, and match it against the request's
   expected active version ID and digest;
5. resolve the request's exact five Profile values against the committed static Catalog;
6. require the resolved Profile purpose and recipe variant to match the subject variant;
7. derive the exact existing character or scene reference render input;
8. render the exact Prompt bytes and zero-authority Receipt with the existing Phase 1 renderer;
9. construct the complete explicit Artifact projection and calculate its new semantic digest; and
10. fully revalidate the returned Artifact before returning it.

Any failure occurs before an Artifact is returned. There is no partial result, default source,
fallback Profile, latest-version discovery, best-effort normalization or external action.

The function does not call `compile_creative_sample`, does not return a base compilation and does
not bind a complete Creative Sample specification. Full-spec batch compilation may later be built
as orchestration over independently valid single-subject calls, but its ordering, collection
identity and failure policy require a separate amendment or ADR.

## Exact subject boundary

`subject` is used only to establish the identity and Bible-declared imported-primary-asset closure
of one reference subject.

For a character call:

- the exact type is `CharacterBible`;
- `request.asset_purpose` is `CHARACTER_REFERENCE_ASSET`;
- `request.subject_id` equals `subject.character_id`;
- `request.reference_source.source_kind` is `CHARACTER_REFERENCE_SOURCE`;
- exactly one member of `subject.asset_versions` has ID
  `subject.active_asset_version_id`; and
- that Bible-declared active `CharacterAssetVersion` has the same `character_id`,
  `media_type=image/png`, a valid content SHA-256 and the released provenance literal
  `IMPORTED_APPROVED_MEDIA`.

For a scene call:

- the exact type is `SceneBible`;
- `request.asset_purpose` is `SCENE_REFERENCE_ASSET`;
- `request.subject_id` equals `subject.scene_id`;
- `request.reference_source.source_kind` is `SCENE_REFERENCE_SOURCE`;
- exactly one member of `subject.asset_versions` has ID `subject.active_asset_version_id`; and
- that Bible-declared active `SceneAssetVersion` has the same `scene_id`, `media_type=image/png`, a
  valid content SHA-256 and the released provenance literal `IMPORTED_APPROVED_MEDIA`.

The caller supplies `expected_active_asset_version_id` and
`expected_active_asset_content_sha256` only as a fail-closed expectation. The Compiler must derive
the actual binding from the exact supplied Bible value and require exact equality. The expectation
cannot construct, select, replace or override a Bible binding. The caller never supplies a
render-input binding. The Compiler rejects any missing, duplicate, inactive, cross-Bible, malformed
or expectation-mismatched value.

The Artifact intentionally does not hash or embed the complete Bible or inactive AssetVersions. Two
fully valid supplied Bibles with the same subject ID and identical Bible-declared active version ID
plus content digest belong to the same relevant source-binding equivalence class, even if their
inactive version history differs. Source closure proves only that the exact Bible supplied to that
Compiler or source-closure operation declares the embedded binding active. It cannot prove the
complete Bible bytes used at the earlier compilation time, external freshness or revocation status.

The following Bible and AssetVersion text fields are never copied, tokenized, summarized,
interpreted or used as defaults or fallback authoring input:

```text
CharacterBible.name
CharacterBible.visual_description
SceneBible.name
SceneBible.visual_description
CharacterAssetVersion.visual_description
SceneAssetVersion.visual_description
CharacterAssetVersion.approval_ref
SceneAssetVersion.approval_ref
```

The existing subject and AssetVersion IDs indirectly bind some of those released fields because
their current ID derivations already do so. That identity closure is not permission to reuse the
literal text in a Prompt and must not be represented as such.

## Future formal request contract

Under a separately approved conforming BUILD, the first new top-level model is
`CreativeSampleReferenceVisualPromptCompileRequestV1`. Its committed file will be
`schemas/CreativeSampleReferenceVisualPromptCompileRequestV1.schema.json`.

It is a strict, frozen Pydantic v2 contract. Unknown fields, scalar coercion, subclass values,
noncanonical text and post-construction mutation fail closed. Its inline source tagged union is
closed and creates no additional top-level Schema or Registry entry.

The request contains exactly these semantic fields:

```text
schema_version=1.0.0
request_purpose=COMPILE_OFFLINE_REFERENCE_VISUAL_PROMPT
source_contract=CHARACTER_OR_SCENE_BIBLE_V1
selection_scope=ONE_REFERENCE_SUBJECT
asset_purpose
subject_id
expected_active_asset_version_id
expected_active_asset_content_sha256
reference_source
catalog_version
catalog_sha256
profile_id
profile_version
profile_sha256
selection_decision_kind=HUMAN_DECISION
selection_decision_ref
authoring_decision_kind=HUMAN_DECISION
authoring_decision_ref
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

`source_contract=CHARACTER_OR_SCENE_BIBLE_V1` is an ADR-042 logical discriminator for the closed
union of the currently released `CharacterBible` and `SceneBible` contracts. It is not the name of
an existing Pydantic class or Schema and does not claim that either Bible has
`schema_version=2.0.0`.

`asset_purpose` permits only `CHARACTER_REFERENCE_ASSET` or `SCENE_REFERENCE_ASSET`. `subject_id`,
`expected_active_asset_version_id`, `profile_id`, `selection_decision_ref` and
`authoring_decision_ref` use the ADR-040 `PortableId` codec. `catalog_version` and
`profile_version` use its `SemanticVersion` codec. `expected_active_asset_content_sha256`,
`catalog_sha256` and `profile_sha256` use `LowerSha256`.

The expected active ID and digest bind the human input packet to one exact anticipated primary
media version. They grant no asset approval or authority. The Compiler uses only the derived Bible
binding to build `render_input` and fails before rendering if either expectation differs.

`selection_decision_kind/ref` is the caller's explicit assertion that a human selected those exact
five Profile values for this offline operation. `authoring_decision_kind/ref` is the caller's
explicit assertion that a human supplied the complete `reference_source` text. The Compiler can
validate their shapes and bind them into the Artifact, but cannot authenticate the decisions,
locate an external review record or prove that the text is first-party, licensed, nonsensitive or
fit for remote processing. Neither assertion grants Rights, Qualification or execution authority.

The request has no independent `request_sha256` in v1. Every semantic request field is repeated in
the Artifact and closed by `artifact_sha256`. If a future workflow persists, signs or independently
exchanges authoring requests, it must first define a separately versioned request identity and a
unique domain rather than inventing one from Pydantic serialization.

## Explicit reference-source tagged union

`reference_source` is exactly one of two inline variants. It contains all story-specific semantic
text that may enter the reference render input. It contains no Bible, AssetVersion, Profile,
Snapshot, Prompt, Provider or Candidate object.

### Character reference source

```text
source_kind=CHARACTER_REFERENCE_SOURCE
narrative: TrimmedText(1..4000)
visual_direction: TrimmedText(1..4000)
action: TrimmedText(1..2000)
emotion_direction: TrimmedText(1..512)
wardrobe_direction: TrimmedText(1..512)
continuity_notes: TrimmedText(1..2000)
```

For one character subject, the Compiler derives the existing
`CharacterReferencePromptRenderInput` exactly as follows:

| Render-input field | Authoritative source |
| --- | --- |
| `input_kind` | fixed `CHARACTER_REFERENCE_ASSET` |
| `narrative` | `reference_source.narrative` |
| `visual_direction` | `reference_source.visual_direction` |
| `action` | `reference_source.action` |
| `emotion_by_character` | exact one-item map `subject_id -> emotion_direction` |
| `wardrobe_by_character` | exact one-item map `subject_id -> wardrobe_direction` |
| `continuity_notes` | `reference_source.continuity_notes` |
| `character_asset_bindings` | exact one-item binding derived from the Bible-declared active CharacterAssetVersion and cross-checked against both request expectations |

The one-item maps and binding tuple use the existing canonical order. No second character,
dialogue, scene, camera, prop or shot field may be injected into this variant.

### Scene reference source

```text
source_kind=SCENE_REFERENCE_SOURCE
narrative: TrimmedText(1..4000)
visual_direction: TrimmedText(1..4000)
action: TrimmedText(1..2000)
props: 0..16 unique TrimmedText(1..128) values in ascending Unicode code-point order
continuity_notes: TrimmedText(1..2000)
```

For one scene subject, the Compiler derives the existing `SceneReferencePromptRenderInput` exactly
as follows:

| Render-input field | Authoritative source |
| --- | --- |
| `input_kind` | fixed `SCENE_REFERENCE_ASSET` |
| `narrative` | `reference_source.narrative` |
| `visual_direction` | `reference_source.visual_direction` |
| `action` | `reference_source.action` |
| `props` | the already canonical `reference_source.props` tuple |
| `continuity_notes` | `reference_source.continuity_notes` |
| `scene_asset_binding` | derived from the Bible-declared active SceneAssetVersion and cross-checked against both request expectations |

No character, dialogue, camera or shot field may be injected into this variant. The Compiler
rejects noncanonical `props`; it does not sort or deduplicate caller input.

Both variants use ADR-040's frozen exact-scalar, NFC, control-code and end-trim rules. No value may
come from an environment variable, current directory, file discovery, clock, random source,
dynamic expression or model inference.

## Admission resource bounds

This boundary admits `1..64` AssetVersions in the supplied Bible. It otherwise leaves the released
Bible contract unchanged.

Raw JSON admission counts the exact supplied bytes, including whitespace and any terminal LF,
before parsing. For `model_validate_json(str)`, the count is exactly
`len(value.encode("utf-8"))`, and an encoding failure rejects the value. For `bytes` or `bytearray`,
the count is exactly `len(value)` before decoding. Raw Request JSON must not exceed 262144 bytes;
raw Artifact JSON must not exceed 524288 bytes. Oversized raw input fails before parsing, so
whitespace cannot bypass the limit. Duplicate object keys, non-finite numbers, a BOM, CR,
non-UTF-8 bytes, non-NFC strings and a container depth above the ADR-040 maximum of 16 fail closed.

For an already constructed in-memory value, resource measurement uses the persistent canonical
document codec frozen below. A Request must not exceed 262144 bytes. An Artifact or the
resource-only full released-field representation of a supplied Bible must not exceed 524288 bytes.
The Bible representation uses every released field, including inactive AssetVersions, solely for
resource accounting. It is not hashed, persisted, exposed as a public identity API or treated as a
new semantic projection. The Prompt retains its independent `1..65536` byte limit.

These are fail-closed resource-admission limits, not new identities. They must be checked before
expensive traversal where possible and do not authorize truncation, omission or normalization.

## Exact five-value Profile resolution

The request supplies these five values explicitly:

```text
catalog_version
catalog_sha256
profile_id
profile_version
profile_sha256
```

The Compiler imports only the generated `VISUAL_PROMPT_CATALOG` shipped with the package. It does
not read the source JSON, discover a Catalog from the filesystem, accept a caller-provided Catalog
or Snapshot, consult an environment variable, choose a default, resolve `latest` or fall back to a
different Profile.

The existing Phase 1 resolver must establish all of the following:

- the supplied Catalog version and digest match the generated Catalog;
- the Profile ID and version match exactly one entry;
- the Profile digest matches its complete semantic projection;
- Profile purpose equals the request's exact reference asset purpose;
- `offline_render_admission_status=HUMAN_REVIEWED_FOR_OFFLINE_RENDER`;
- `profile_text_provenance_status=FIRST_PARTY_TEXT_REVIEWED`; and
- `shot_type=REFERENCE_SHEET` and `narrative_contexts` includes `REFERENCE_DEVELOPMENT`;
- the Profile carries the exact matching character or scene reference recipe variant; and
- both the Profile and recipe role tuples equal the complete three-role character tuple or complete
  four-role scene tuple frozen below; an otherwise ADR-040-valid subset is rejected in this V1.

`DRAFT`, `RETIRED`, `RIGHTS_REVIEW_REQUIRED`, `PROHIBITED_EXTERNAL_CONTENT`, a wrong purpose, a
wrong recipe or any five-value mismatch fails closed. Provider compatibility metadata never
participates in admission, selection or authority.

The resolver returns the internal resolver-only `VisualPromptProfileSnapshot`. The public Compiler
entrypoint never accepts a caller-constructed Snapshot.

The Phase 1 loader validates only the generated Catalog available in the current package and does
not itself provide immutable Catalog history. A verifier can recompute embedded Profile, input,
Prompt, Receipt and Artifact integrity without that historical Catalog, but must not claim to have
re-proved historical offline-render admission unless the exact
`catalog_version + catalog_sha256` value remains available to the resolver.

## Snapshot projection

The Artifact's `profile_snapshot` uses the exact 14-key flattened ADR-040 projection. The following
is its documentation order; canonical JSON hashing sorts object keys and does not treat Python or
Schema insertion order as identity:

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

A future BUILD adds parallel closed Character and Scene nested Snapshot definitions for this
Artifact. It must not generalize, import-reinterpret or modify ADR-041's narrative-only
`_VisualPromptProfileSnapshotV1`, whose purpose, recipe and context closure remains unchanged.

For a character Artifact, `reference_asset_recipe` is exactly the complete
`CharacterReferenceAssetRecipe` projection and `reference_asset_types` equals the exact full
three-role character tuple. For a scene Artifact, both values use the exact scene variant and full
four-role tuple. The top-level and recipe tuples must be identical. They are not generalized,
converted, reordered, reduced or admitted as subsets in this V1.

The Snapshot includes `constraint_set.qc_expectations` because it is Profile semantics.
`qc_expectations` never enters Prompt bytes and never becomes a QC observation or fact. Positive
and negative Prompt constraints enter Prompt bytes under the existing renderer grammar, but their
presence does not prove that an output satisfies them.

Catalog entry display text, reviewer values, admission status and Provider compatibility
observations are not literal Snapshot fields. Their indirect inclusion in the accepted Catalog
digest grants no authority.

## One composite reference-sheet Prompt

Each call renders exactly one Prompt and one Receipt for exactly one subject. The existing Profile
recipe is included in that Prompt using the accepted Phase 1 renderer grammar.

The character Profile and recipe must contain exactly this complete tuple in this order:

```text
CHARACTER_IDENTITY_SHEET
CHARACTER_POSE_REFERENCE
CHARACTER_EXPRESSION_REFERENCE
```

The scene Profile and recipe must contain exactly this complete tuple in this order:

```text
SCENE_ESTABLISHING_REFERENCE
SCENE_LIGHTING_REFERENCE
SCENE_MATERIAL_REFERENCE
SCENE_PROP_PLACEMENT_REFERENCE
```

Those role literals describe required text and layout semantics within one composite
reference-sheet Prompt. They do not mean one Prompt per role, do not identify media slots and do
not create three character-role outputs, four scene-role outputs or a seven-output cross-purpose
batch. They also do not prove that a future Provider will return one image, a fixed panel count or
any media. The first slice has no role-to-image mapping, role-specific content digest,
role-specific Candidate, Provider input material or role-specific AssetVersion.

Changing from one composite Prompt to per-role Prompts would change cardinality, identity and
future Provider semantics. It requires a new version and a separately accepted decision.

## Future formal Artifact contract

Under a separately approved conforming BUILD, the second new top-level model is
`CreativeSampleReferenceVisualPromptArtifactV1`. Its committed file will be
`schemas/CreativeSampleReferenceVisualPromptArtifactV1.schema.json`.

It is a strict, frozen Pydantic v2 contract. Its inline source, Snapshot, render-input and Receipt
definitions are closed and create no additional top-level Schema or Registry entry.

The Artifact contains exactly these top-level fields:

```text
schema_version=1.0.0
artifact_purpose=OFFLINE_REFERENCE_VISUAL_PROMPT_ARTIFACT
source_contract=CHARACTER_OR_SCENE_BIBLE_V1
selection_scope=ONE_REFERENCE_SUBJECT
asset_purpose
subject_id
expected_active_asset_version_id
expected_active_asset_content_sha256
reference_source
selection_decision_kind=HUMAN_DECISION
selection_decision_ref
authoring_decision_kind=HUMAN_DECISION
authoring_decision_ref
profile_snapshot
render_input
render_input_sha256
prompt
prompt_sha256
prompt_size_bytes
prompt_render_receipt
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
artifact_sha256: LowerSha256
```

`reference_source` repeats the complete request variant, not merely a decision reference.
`profile_snapshot` carries all five selection values through its Profile and Catalog identity
fields. Every request semantic field except the fixed request-purpose literal is therefore either
repeated directly or represented by the Artifact's distinct fixed purpose. Request and Artifact
purpose literals cannot be substituted for one another.

The two expected active-binding fields repeat the request values and must equal the sole binding in
the exact nested render-input variant. This duplication is an intentional fail-closed
request-to-derived-source cross-check, not a caller override path.

`render_input` is exactly one complete existing `CharacterReferencePromptRenderInput` or
`SceneReferencePromptRenderInput` projection matching `asset_purpose`, `subject_id`, source tag,
Profile purpose and exact subject type. The nested variant is not a caller-provided arbitrary map.

`render_input_sha256` reuses the existing domain-separated render-input digest. `prompt` is the
exact decoded UTF-8 Prompt text and must be NFC, use LF only, contain no BOM or trailing horizontal
whitespace and end with exactly one LF. Encoding it as UTF-8 must reproduce the renderer bytes.
`prompt_sha256` is the raw SHA-256 of those bytes. `prompt_size_bytes` is their exact length in
`1..65536`.

`prompt_render_receipt` is the complete existing Prompt Receipt document projection, including its
own digest and every direct zero-authority field. It is produced by the existing renderer and never
accepted from the request. The Artifact rejects any mismatch among its Snapshot, render input,
input digest, Prompt bytes, raw Prompt digest, byte count or Receipt.

The Artifact contains no `Candidate`, media, output URL, local media path, Provider/model, task ID,
Attempt, retry counter, Qualification, Rights Manifest, QC result, publication state or promotion
state. It is an immutable offline Prompt and process-evidence value, not a runnable job, generated
asset, approval or authorization.

## Artifact identity

This Accepted ADR reserves and freezes exactly one new semantic digest domain:

```python
b"sdc:visual-prompt-reference-compiler-artifact:v1\0"
```

`artifact_sha256` is SHA-256 over the domain prefix followed by the canonical compact UTF-8 JSON
projection of every Artifact field except `artifact_sha256` itself. The projection is explicit and
closed. It uses sorted object keys, compact separators, unescaped NFC Unicode and the exact array
orders defined here and in ADR-040. It is never derived from incidental Pydantic, dataclass or
`__dict__` serialization.

Every semantic field, including all direct zero-authority values, complete authoring source,
decision references, Snapshot, render input, exact Prompt, Receipt and their repeated digests,
participates in the Artifact projection. Mutating any one field must invalidate the Artifact.

The existing domains are reused without modification for:

- Profile identity;
- Catalog identity;
- render-input identity;
- Prompt Receipt identity.

The existing Catalog Digest Receipt domain remains unchanged but is not read, calculated or
embedded by this Compiler boundary.

The Prompt digest remains raw SHA-256 over exact Prompt bytes and has no domain prefix. The
ADR-041 narrative sidecar domain is not reused. `stable_id` is not used for this Artifact.

No independent source, request, subject-Bible or complete-AssetVersion-projection digest is added in
v1. The expected raw media content SHA-256 remains explicit, the complete authoring source is
embedded, the Bible-derived binding is embedded in `render_input`, and released subject and
AssetVersion identities retain their current semantics. Adding a new independent identity later
requires an explicit projection, unique domain, versioning and known-answer review.

## Validation operations and claim levels

Three claim levels must remain distinct, but V1 exposes only the Compiler entrypoint and normal
Artifact model validation. It does not add a public verifier API.

Artifact model validation is integrity-only. `model_validate` or `model_validate_json` validates
the Artifact's explicit projection, Snapshot semantics and render-input digest, then locally
re-renders from the complete embedded reference Snapshot plus exact embedded render input using the
existing Phase 1 renderer grammar. It must byte-compare the resulting Prompt and complete Receipt
with the embedded Prompt and Receipt before validating the raw Prompt digest, byte size and
Artifact digest. A self-consistent replacement Prompt plus recomputed raw/Receipt/Artifact hashes
must fail if it is not the exact renderer result.

This local re-render performs no filesystem, Bible, Catalog, environment or network lookup. A
future implementation may use a private integrity-only bridge from the closed formal reference
Snapshot to the existing renderer semantics, but it must not expose a public Snapshot constructor,
bypass the five-value resolver in the Compiler entrypoint or represent that bridge as Catalog
admission. Artifact model validation cannot prove that the embedded binding is active according to
an external or later Bible value or that the Profile was admitted by an unavailable historical
Catalog.

The Compiler entrypoint additionally performs source closure against the exact supplied
`CharacterBible` or `SceneBible`. It proves that this supplied value declares the expected and
embedded AssetVersion binding active. It does not hash the complete Bible into the Artifact and
does not prove the exact inactive-version history or full Bible bytes present at an earlier
compilation time. It still cannot prove media ownership, license, privacy clearance,
commercial-use rights, freshness, revocation status or source-text authorship.

The same Compiler call performs offline admission against the package's current static Catalog.
Historical admission is a claim limitation, not another V1 API: re-proving it later requires the
exact Catalog identified by `catalog_version + catalog_sha256`. If that Catalog is unavailable, a
consumer must report that admission could not be re-proved rather than supplying a Catalog to this
Compiler, changing model validation or inferring admission from the embedded Snapshot.

## Public validation error boundary

The future module defines `VisualReferencePromptCompilerError(ValueError)` for entrypoint type,
cross-object closure, resolver, renderer and constructed-Artifact failures. Direct Request or
Artifact construction and JSON admission use normal `pydantic.ValidationError`. The entrypoint
requires an exact Request type, rejects subclasses and fully revalidates the complete Request to
defeat forged construction or `model_copy` values. It converts that failure and any internal
Profile, render or Artifact validation failure to `VisualReferencePromptCompilerError` while
preserving the original exception as the cause. It returns no sentinel, partial Artifact or error
object. Exception classes, cause preservation and absence of a partial result are stable; exact
human-readable error messages are not a compatibility interface.

## Persistent document and known-answer boundary

Persistent canonical JSON is NFC UTF-8, uses `ensure_ascii=false`, sorted object keys, two-space
indentation and LF line endings, contains no BOM or CR, and ends with exactly one LF. It rejects
duplicate keys and non-finite numbers. The terminal LF and indentation are persistent file-format
bytes and are excluded from domain-separated compact semantic projections.

A future BUILD freezes these exact paths:

```text
human source packet:
  tests/fixtures/visual_prompt_profiles/reference-compiler/reviewed-known-answer-source-v1.json
derived fixture:
  tests/fixtures/visual_prompt_profiles/reference-compiler/generated-known-answer-v1.json
generator:
  src/sdc/visual_reference_prompt_compiler_codegen.py
```

Both JSON files use the persistent document codec above. The human source packet contains the
complete synthetic Bible and Request inputs but no generated expected Artifact. The derived fixture
contains each complete embedded source, Snapshot, render input, Prompt, Receipt and Artifact result.
Nested source, render-input and Receipt values are not separate persistent files; their cross-host
byte claim refers to their canonical projection inside the derived fixture, while Prompt byte claims
continue to use exact decoded UTF-8 Prompt bytes and the existing raw Prompt SHA-256.

The human source packet has frozen raw SHA-256 and byte-size constants. No generator mode may write
it. A future generator supports only mutually exclusive explicit `--check` and `--update` modes:
`--check` is completely read-only; `--update` has the single fixed write allowlist consisting only
of the derived fixture path above. The source packet can change only through a direct human edit,
new frozen raw fingerprint, visible diff and renewed explicit human approval. The two frozen
fingerprint constants live only in
`src/sdc/visual_reference_prompt_compiler_codegen.py`; they are not Artifact fields, authority
evidence or a second source identity domain.

## Zero-authority and rights boundary

The request, Artifact and nested Prompt Receipt each carry direct false/zero authority fields.
Valid Profile admission, deterministic rendering, valid hashes or a human decision reference can
never change those values.

The Catalog's `qualification`, `rights` and `compatibility` metadata remain descriptive status
markers only. They grant no Provider Authority, execution permission, commercial authorization or
asset-promotion eligibility. Provider compatibility is not copied into the Artifact and must not
select a Provider or syntax route.

`PromptRenderReceipt` remains process evidence only. It is not proof of rights, source authorship,
review authenticity, Profile quality, QC satisfaction, Provider capability or approval. It does
not replace a Rights Manifest and does not constitute a release decision.

A Bible-declared active AssetVersion states `IMPORTED_APPROVED_MEDIA`, but this Compiler boundary
does not authenticate `approval_ref`, inspect the media, determine who owns it, establish freshness
or revocation status, or establish that it may be sent to a Provider. Binding that AssetVersion
into a Prompt input is not commercial-use or remote-processing authorization.

The explicit authoring decision reference is likewise an input assertion, not first-party
provenance evidence. Local reference text may contain private, sensitive or third-party material.
Successful local compilation does not clear that text for retention, training, publication or any
remote operation.

## Prompt, QC and Provider responsibility isolation

The three Profile semantic areas remain separate:

- positive and negative Prompt constraints are deterministic Prompt text;
- `qc_expectations` are Profile-bound expectations that do not enter Prompt bytes and do not
  become QC facts; and
- Provider compatibility observations are Catalog metadata that neither enter the Prompt Artifact
  nor authorize Provider selection or execution.

This ADR does not invoke or modify `qc.verify`. A constraint or expectation cannot reserve an
Attempt, initiate Retry, produce `STOP-2`, qualify an asset or authorize publication.

The request and Artifact are not Rights Manifests. They directly state
`replaces_rights_manifest=false` and `grants_rights=false`.

## Runtime and execution isolation

The future types, if implemented, are offline Compiler evidence and must be structurally and
operationally isolated from execution:

- no `GenerationJob`, `JobGraph`, `ProviderRequest` or Provider input material accepts them;
- no Temporal workflow accepts them as input;
- no client, workflow, worker, Runtime, Provider or QC module imports the future module;
- no Provider adapter accepts their Prompt, Snapshot, Receipt or active asset binding;
- no credential, environment variable, filesystem discovery, clock, random value or network call is
  read during compilation;
- no media is created, uploaded, downloaded, copied, retained, published or trained on;
- no Candidate or AssetVersion is created or modified; and
- every direct authority, cost and count field remains its exact frozen false or zero value.

The future compiler and codegen modules must not import `sdc.schemas`. Registry wiring is one-way:
`sdc.schemas` may import the two top-level models only after implementation approval. Existing
Runtime, Provider, client, worker, workflow and QC modules must not acquire a reverse import.

The existence or validity of an Artifact cannot activate the existing structural Attempt ceiling on
another contract. `authorized_attempts=0` permits no Attempt and `provider_requests=0` permits no
Provider call.

The future Request and Artifact must be structurally rejected by `GenerationJob`, `JobGraph`,
Provider request, Canary execution and any current Runtime payload boundary. Duck typing or a
shared field name cannot make them executable.

## Generated-reference Candidate provenance boundary

Offline rendering of a reference Prompt is not Candidate creation. This ADR produces no generated
media and does not define a generated-reference Candidate.

Current `CharacterAssetVersion` and `SceneAssetVersion` contracts truthfully support only
`provenance=IMPORTED_APPROVED_MEDIA`. Generated content cannot be relabeled under that literal,
even after download, manual review or re-import. That is a permanent fail-closed rule for these
contract versions.

A later generated-reference Candidate path requires a separate provenance and Qualification ADR.
It must define Candidate identity, Provider and Attempt evidence, Profile/Snapshot/input/Prompt/
Receipt binding, media content hashes, privacy and retention evidence, human Qualification, Rights
Manifest integration, revocation and promotion semantics. This ADR grants no advance approval for
that work and does not start it.

## Multiple reference-role Provider-input boundary

This slice preserves exactly one active primary AssetVersion per Bible and one composite reference
Prompt per call. It does not define multiple role-specific images or bind them to any Provider.

If a future Provider route requires simultaneous role-specific media, a separate Provider-input ADR
must define at least:

- pre-promotion Candidate and post-promotion AssetVersion lifecycle states;
- an append-only V2 asset binding or Provider input-material contract;
- exact role cardinality and canonical order;
- role-to-media identity and content-hash binding;
- media count, type and size limits;
- persistence, privacy and Rights closure;
- Provider request and idempotency impact; and
- fail-closed zero-authority behavior until all required gates close.

Existing AssetVersion contracts must not be extended or reinterpreted in place. Neither an
accepted Profile recipe nor this offline Artifact resolves the later Provider-input problem.

## Failure behavior

The future Compiler boundary fails closed for at least:

- a value that is not one exact revalidated `CharacterBible` or `SceneBible`;
- a request asset purpose, source tag, subject ID or Bible type mismatch;
- a missing, duplicate, inactive, malformed or cross-Bible AssetVersion;
- a Bible-declared active asset whose subject, ID, content digest, media type or released provenance
  is invalid;
- an expected active version ID or digest that differs from the binding derived from the Bible;
- any attempt to construct or override a render-input binding through the request;
- any use of Bible/AssetVersion descriptions, names, approval references, shot text or dialogue as
  authoring defaults;
- any Profile or Catalog identity mismatch;
- an inadmissible, retired, draft, rights-review-required or prohibited-external-content Profile;
- a Profile purpose or reference recipe variant mismatch;
- any character role tuple other than the exact full three-role tuple or scene tuple other than the
  exact full four-role tuple;
- a caller-constructed Catalog or Snapshot;
- an unknown field, coercible scalar, subclass value, noncanonical string or unrecognized enum;
- a noncanonical, duplicate or oversized scene props tuple;
- any source-to-render-input field or ordering mismatch;
- any Snapshot, recipe or role mismatch;
- any Prompt byte, raw digest or size mismatch;
- any Receipt field or semantic digest mismatch;
- any Artifact field or semantic digest mismatch;
- any non-false/non-zero authority value; and
- any attempt to send the request or Artifact into an execution path.

Failure returns no Artifact and performs no filesystem write, persistence, external call or other
side effect. It never falls back to a narrative Profile, arbitrary Bible description, default
Profile, latest Catalog entry or existing Creative Sample Prompt.

## Future validation and implementation gates

Acceptance does not authorize implementation. A conforming separately approved BUILD must prove at
least:

1. current authoritative `main`, baseline and all three ADR dependencies before editing;
2. exactly two new top-level models, exactly two new Schema files and Registry growth from 70 to
   exactly 72;
3. byte-for-byte equality of all 70 pre-integration committed Schemas and exact preservation of
   `MODELS[:70]`;
4. strict, frozen, all-fields-required Request and Artifact values with closed inline definitions;
5. rejection of unknown fields, scalar coercion, subclass values, forged `model_copy` values and
   cyclic or dynamically typed structures;
6. exact character/scene source union, field bounds, source tag and purpose closure;
7. direct proof that every render-input semantic field has exactly one source named by this ADR;
8. no read or copy dataflow from any Bible/AssetVersion name, `visual_description`, `approval_ref`,
   shot or dialogue field into Prompt semantics;
9. exact Bible-declared active AssetVersion closure, including subject ID, released ID, media type,
   provenance and content SHA-256, plus equality with both request expectations;
10. exact five-value static-Catalog resolution with no default, latest, fallback or Agent selection;
11. exact matching parallel character or scene flattened Snapshot, typed recipe and required full
   three-role or four-role tuple, with no ADR-041 nested-model modification;
12. exact reuse of existing Profile, Catalog, render-input and Receipt digest domains;
13. independent calculation of the literal new Artifact domain and explicit projection;
14. mutation of every Artifact semantic field changing or invalidating `artifact_sha256`;
15. integrity-only local re-render from the embedded Snapshot and input, exact Prompt/Receipt byte
   comparison, and rejection of a non-renderer Prompt even when every enclosing hash is recomputed;
16. exact raw Prompt SHA-256 and byte-size verification;
17. one and only one composite Prompt/Receipt per subject, never one output per recipe role;
18. byte-identical persistent source packet and derived fixture bytes, identical canonical nested
   source/input/Receipt projections, and exact Prompt bytes across supported Windows and Linux;
19. unchanged v1 Compiler canonical output and identities;
20. unchanged Creative Sample v2 output, Prompt, IDs, Pilot compilation identity and job keys;
21. unchanged ADR-041 Request, narrative sidecar, known answers and sidecar digest;
22. proof that QC expectations do not enter Prompt bytes or QC decisions;
23. proof that Provider compatibility does not enter selection, Artifact or authority;
24. proof that Catalog, human-decision references, Receipt and Artifact grant no Rights,
   Qualification or execution;
25. proof that no Candidate, media, role binding, AssetVersion or promotion result is created;
26. structural rejection by Runtime, JobGraph, Provider request and Canary execution paths;
27. static and runtime denial of network, credentials, environment, clock, randomness, persistence
   and dynamic import inputs at the Compiler entrypoint, Request and Artifact validation, and the
   public projection and hash helpers; codegen is outside this no-persistence runtime scope,
   `--check` is wholly read-only and `--update` writing exactly the fixed derived-fixture allowlist
   above is the sole persistence exception, granting no other file or operation persistence
   authority;
28. exact raw and in-memory resource size, depth and asset-version-count boundaries;
29. `pydantic.ValidationError` versus `VisualReferencePromptCompilerError` behavior;
30. integrity-only model validation with no hidden Catalog/Bible lookup, exact-Bible Compiler source
   closure and honest historical-Catalog admission limitations; and
31. complete offline `make check` success with no paid or remote service call.

The implementation review must include complete human-readable known-answer packets for at least:

- one basic character reference source and full rendered Prompt;
- one Unicode/NFC character reference source and full rendered Prompt;
- one basic scene reference source with empty props and full rendered Prompt; and
- one Unicode/NFC scene reference source with multiple canonically ordered props and full rendered
  Prompt.

Each packet must show the complete request input, expected and derived Bible-declared active
binding, exact five Profile values,
flattened Snapshot, complete render input, input digest, exact Prompt, raw Prompt digest, byte size,
complete Receipt, Artifact and Artifact digest. The fixture source text must be first-party synthetic
content and receive explicit human source review. No generator mode can rewrite the approved source
packet; any source change follows the direct human-edit, fingerprint and re-approval path above.

An implementation PR must remain Draft until the packets, both new Schemas, the old-70 Schema byte
proof and all relevant negative boundaries receive explicit human review. Acceptance of this ADR is
not approval of an implementation PR.

## Contract and Schema impact

This ADR-only decision changes no Contract, Schema or Registry entry.

If separately authorized and implemented exactly, the append-only impact is:

```text
CreativeSampleReferenceVisualPromptCompileRequestV1
CreativeSampleReferenceVisualPromptArtifactV1
```

There will be exactly two new committed Schemas and `sdc.schemas.MODELS` will grow from 70 to 72.
The append order is frozen: `MODELS[70]` is
`CreativeSampleReferenceVisualPromptCompileRequestV1`, and `MODELS[71]` is
`CreativeSampleReferenceVisualPromptArtifactV1`.
The source tagged union, Snapshot variants, render-input variants and Receipt projection remain
closed inline definitions rather than additional top-level Registry models.

No existing Contract gains an optional field. No existing model is reinterpreted as the Artifact.
No current internal Phase 1 dataclass becomes a released top-level contract merely because its
projection is nested in the new Artifact.

## Rejected alternatives

The following alternatives are rejected for the first slice:

- derive reference authoring text from Bible or AssetVersion `visual_description`;
- copy Bible display names or `approval_ref` values into Prompt text;
- infer reference directions from arbitrary narrative shots or dialogue;
- accept a full `CreativeSampleSpec` and batch all Bibles in the first contract;
- call `compile_creative_sample` or bind the existing base compilation identity;
- replace or extend the ADR-041 narrative sidecar with reference variants;
- emit one Prompt, Receipt, Candidate or media slot per recipe role;
- let the caller construct a render-input binding, use expected active ID/hash values to override
  the Bible, or supply Catalogs or Snapshots;
- choose a Profile by purpose alone, default, latest version, fallback or Agent judgment;
- reuse the narrative sidecar digest domain or a `stable_id` helper;
- rely on incidental Pydantic/dataclass serialization for Artifact identity;
- add four top-level character/scene-specific Request and Artifact contracts;
- add fields to current Bible, AssetVersion, `InputMaterial`, `GenerationJob` or Provider request
  contracts;
- name the offline Artifact a Candidate, generated asset or qualification result; and
- connect the first slice to Runtime, Provider, QC, Rights, Qualification or publication.

## Risks and treatment

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking | Reference Prompt semantics have no unambiguous released authoring source | Require one complete caller-supplied tagged source plus an unauthenticated human-authoring assertion; prohibit all implicit Bible, asset, shot and dialogue derivation |
| Blocking | A human authoring reference is mistaken for proof of first-party provenance or rights | Bind the assertion for traceability while explicitly treating it as an unauthenticated, zero-authority input claim |
| Blocking | Recipe role admission or cardinality is ambiguous | Require the exact full three-role/four-role tuple, one Bible to one composite reference-sheet Prompt and one Receipt; keep roles descriptive only |
| Blocking | Character/scene source, Profile, recipe, render input and active asset cross variants | Require exact tagged-union and Bible-type closure at every nested boundary and fail closed |
| Blocking | A request is replayed after the Bible-declared active media changes | Bind the expected active AssetVersion ID and content digest in the Request and Artifact; derive and cross-check rather than override |
| Blocking for later Candidate work | Generated media cannot truthfully use the released imported-media provenance literal | Create no Candidate or promotion; require a separate provenance and Qualification ADR |
| Blocking for later Provider work | Multiple role-specific media lack an approved lifecycle and Provider input contract | Create no role binding or Provider input; require a separate append-only Provider-input ADR |
| Important | Artifact integrity is mistaken for proof of external freshness or active state | Separate integrity-only validation from closure against the exact supplied Bible and state the non-proofs |
| Important | Embedded Profile identity is mistaken for renewed historical admission | Require the exact historical Catalog for an admission claim and report honest unverifiability when absent |
| Important | Bible IDs indirectly bind descriptions and are mistaken for Prompt text reuse | Preserve ID validation but prohibit literal-description dataflow into the authoring source or Prompt |
| Important | New reference contracts drift released outputs or existing Schema bytes | Use a new isolated module, append exactly two Schemas and hash all 70 existing Schema files |
| Important | Receipt, Catalog or compatibility metadata is mistaken for authorization | Carry direct false/zero fields and exclude Provider compatibility from the Artifact projection |
| Important | Raw Prompt SHA and domain-separated semantic hashes are confused | Reuse each accepted domain exactly and use the unique Artifact domain frozen by this ADR |
| Minor | Full-spec batch orchestration is not included | Defer collection order, batch identity and partial-failure policy |
| Minor | CLI, persistence, display labels and localization are absent | Keep presentation and storage outside the first semantic boundary |

## Non-goals

This ADR does not approve or specify:

- any implementation without separate BUILD approval;
- a formal Contract, Schema, registry update or code generator in this task;
- Profile-driven v1 compilation;
- changes to Creative Sample v2 or the ADR-041 narrative sidecar;
- full-spec or multi-subject batch compilation;
- automated, inferred or model-authored reference directions;
- source-provenance authentication or a first-party text certification system;
- image or video generation;
- a generated-reference Candidate;
- Qualification or AssetVersion promotion;
- multiple reference-role media binding;
- Runtime, Provider/model selection, submission, inspection, download or cancellation;
- Provider credentials, network, remote processing, retention or spending;
- Retry, Creative Attempt 2 or recovery logic;
- automated or semantic QC decisions;
- Rights Manifest creation, finalization or execution;
- publication, posting or training; or
- migration of any existing compiled artifact.

## Permitted claims and explicit non-proofs

Only after a separately approved conforming implementation may SDC claim that one
exact human selection assertion, one unauthenticated human-authoring assertion, one expected and
Bible-derived active binding from the exact supplied Bible value, and one compile-time-admitted
reference Profile deterministically produced one immutable offline composite reference Prompt
Artifact and process Receipt. Renewed historical admission verification remains conditional on
availability of the exact Catalog.

This cannot prove or grant:

- authenticity or sufficiency of either human decision reference;
- first-party provenance, ownership, license or privacy clearance for source text or media;
- the complete Bible bytes present at compilation time, external freshness or revocation status;
- commercial-use, remote-processing, retention, training or publication permission;
- Prompt quality or Provider suitability;
- satisfaction of a positive or negative Prompt constraint;
- QC PASS, retry eligibility or recovery authority;
- Candidate provenance, generated-output rights or media identity;
- Qualification or AssetVersion promotion status;
- Rights Manifest closure;
- Provider capability, entitlement, credential or execution authority; or
- suitability of role-specific media for a future Provider request.

## Consequences

Positive consequences:

- character and scene reference Prompt authoring becomes explicit rather than inferred;
- every render-input field has one named authoritative source;
- the Bible-declared active imported asset identity and content digest are anticipated by the
  Request, derived from the supplied Bible and closed without copying its description into Prompt
  text;
- one subject, one admitted Profile, one composite Prompt and one Receipt form a small deterministic
  unit;
- existing v1, Creative Sample v2 and narrative sidecar bytes and identities remain unchanged;
- zero authority is direct at every future formal boundary; and
- Candidate provenance and multiple-role Provider input remain visibly blocked behind their own
  decisions.

Costs:

- callers must explicitly author reference directions that may duplicate descriptive concepts
  stored elsewhere;
- the first slice processes one subject at a time and has no batch Artifact;
- source-closure verification needs an exact Bible value to prove its declared active binding;
- historical admission verification needs the exact Catalog;
- a later implementation intentionally grows the Registry from 70 to 72; and
- any source, projection, role-cardinality or digest change requires explicit versioning, a unique
  domain and new known-answer review.

Until a separately approved implementation passes its complete review, SDC must continue to claim
that no Character/Scene Reference Prompt Compiler input contract, formal reference Prompt Artifact
or reference Compiler Artifact digest exists.
