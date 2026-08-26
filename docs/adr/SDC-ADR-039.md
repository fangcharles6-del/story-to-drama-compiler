# SDC-ADR-039: Deterministic Visual Prompt Profiles

- Status: Proposed
- Date: 2026-08-26
- Depends on: SDC-ADR-038 / Production Adapter Foundation v1
- Source assessment: `freestylefly/awesome-gpt-image-2@685469889fb72fd5adefae45e1645d527edcb5e7`
- License observed at source revision: MIT
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: repository-owned profile metadata and deterministic local render evidence only;
  no third-party Prompt or image import
- Network/spend boundary: zero new network calls, zero credentials, zero Provider requests

## Context

SDC already compiles an immutable Creative Sample specification into `NIRV2`, `PIRV2`,
`StoryboardShotV2`, `GenerationJob`, `JobGraph` and `AssemblyPlan`. Character and scene Bibles each
close over one active approved PNG `AssetVersion`, and the current Compiler deterministically
renders a shot Prompt with a fixed internal function. The existing path is intentionally narrow:
it has no versioned visual-style profile, no independently auditable Prompt-render receipt and no
structured reference-asset recipe.

SDC-ADR-038 adds a static zero-authority Provider catalog and advisory-only semantic QC boundary.
It does not grant Provider capability or execution authority, and it does not turn a Prompt
constraint into a QC fact. Those boundaries remain authoritative here.

The fixed external source assessment contains useful design ideas: a structured style library,
generated authoring guidance, human-readable galleries and repeatable generators. It also contains
community-collected Prompts and images whose ownership and commercial-use status are not established
by the repository's MIT license. Its image API uses a synchronous, product-specific Provider and
credit flow that conflicts with SDC's durable asynchronous Runtime.

This ADR therefore adopts only the architectural idea of an SDC-authored Prompt-as-Code catalog.
It does not copy external Prompt text or images, vendor external source, install an Agent Skill, or
adopt the external runtime.

Acceptance of this ADR records only the architecture and permits preparation of a separately
reviewed Phase 1 offline BUILD within the boundary below. It does not assert that an implementation
exists, has passed validation or is runnable. It does not approve image generation, a Provider
request, spending, Qualification, asset promotion, publication or any claim of commercial-use
rights.

## External component mapping and disposition

All observations in this table are bound to the exact source assessment revision named above.

| External component | Useful design signal | SDC disposition |
| --- | --- | --- |
| `data/style-library.json` | One structured source can drive multiple views | Use the single-source pattern only; author all SDC profile semantics independently |
| `agents/skills/gpt-image-2-style-library/SKILL.md` and `agents/openai.yaml` | An authoring reference can be generated from structured data | Generate a non-authoritative Agent authoring reference; never install or invoke the external Skill |
| `scripts/generate-style-skill.mjs` | Derived guidance can be checked for freshness | Add an SDC-owned deterministic generator with a check-only mode |
| `scripts/generate-site-data.mjs` | Gallery data can be projected into a presentation view | Keep presentation derived; reject substring/keyword inference as Compiler classification |
| `README.zh-CN.md` and `docs/templates.md` | Broad examples need explicit taxonomy and one source of truth | Do not import examples; use freshness checks to prevent count/content drift |
| `api/generate-image.js` | Generation needs an explicit request boundary | Reject the synchronous endpoint, embedded Provider/model choice and credit flow |
| `LICENSE` and `docs/disclaimer.md` | Repository code and collected community content have different rights boundaries | Treat MIT code as referenceable; treat third-party Prompts and images as prohibited imports |

## Decision

### 1. Prompt-as-Code remains an offline, first-party boundary

SDC will own a versioned catalog of visual Prompt profiles. A profile is declarative content, not
executable code. It contains only allowlisted scalar values, ordered tuples, typed taxonomy values,
fixed section descriptors and fixed placeholder identifiers. It cannot contain Python, callbacks,
imports, expressions, conditionals, network locations, environment references, Provider secrets or
dynamic discovery rules.

Every initial profile must be authored for SDC. External community Prompt text, example images and
template prose are not admissible source material. The fixed external repository is recorded only as
the source assessment that motivated the architecture.

### 2. One structured source is authoritative

Phase 1 will add `src/sdc/visual_prompt_profiles.json` as the one repository-owned source. Loaders
and generators resolve only that exact repository/package-relative identity; current-working-
directory search, environment override and fallback discovery are prohibited. The JSON document is
the only hand-edited semantic source for profiles, constraints, reference recipes, taxonomy
assignments, qualification markers, rights markers and compatibility markers.

The following are deterministic generated artifacts and must not be edited independently:

- `src/sdc/visual_prompt_catalog.py`, consumed by the pure offline renderer;
- `docs/reference/visual-prompt-profiles.md`, the operator reference;
- `docs/reference/visual-prompt-agent-authoring.md`, the non-authoritative Agent authoring
  reference;
- `tests/fixtures/visual_prompt_profiles/generated/`, containing generated golden render fixtures;
- `docs/reference/visual-prompt-catalog-digest-receipt.json`, the Catalog Digest Receipt.

`tests/fixtures/visual_prompt_profiles/reviewed-known-answer-v1.json` is a separate, manually
reviewed known-answer vector. It is not a generated artifact and no ordinary generation command may
rewrite it.

A generator check mode must fail when any generated artifact is missing, stale, reordered or
manually changed. CI uses check mode only. Updating derived artifacts requires an explicit local
update operation and review of the complete diff; ordinary regeneration must never rewrite the
reviewed known-answer vector. Display-only localization may be maintained separately in Phase 2,
but it must not enter a profile's semantic projection or alter Prompt bytes.

The authoritative JSON uses a persistent canonical-document form: UTF-8 without BOM, strings and
object keys already in NFC, recursively sorted object keys, two-space indentation,
`ensure_ascii=False`, `allow_nan=False`, LF only and exactly one terminal LF. Admission rejects
duplicate keys, malformed UTF-8, non-canonical bytes, scalar coercion and repairable variants. This
document form is distinct from the compact JSON projection used for semantic hashes.

Every generated or reviewed JSON document, including both Receipt and known-answer documents, uses
that same persistent canonical-document form. Other generated text files use UTF-8 without BOM,
NFC, LF, no trailing horizontal whitespace and exactly one terminal LF. Generated-artifact path
identities are NFC repository-relative portable paths using `/`; absolute paths, drive prefixes,
empty segments, `.` and `..` are prohibited.

### 3. Phase 1 uses internal frozen value objects

Phase 1 objects must be internal frozen and slotted dataclasses, or an equivalently strict immutable
representation frozen by the separately reviewed BUILD. They are not released Pydantic contracts,
are not added to `sdc.schemas.MODELS`, and do not produce committed JSON Schemas.

| Object | Architectural boundary; not a field-level hash projection |
| --- | --- |
| `PromptConstraintSet` | Ordered positive constraints, ordered negative constraints and separately ordered QC expectations |
| `ReferenceAssetRecipe` | Exact asset purpose, reference roles, required anchors, forbidden drift, layout rules and binding expectations |
| `VisualPromptProfile` | `profile_id`, `profile_version`, semantic taxonomy, renderer version, section order, placeholders, constraint set and optional recipe |
| `VisualPromptProfileSnapshot` | Exact admitted semantic profile plus `profile_id`, `profile_version`, `profile_sha256`, `catalog_version` and `catalog_sha256` |
| `PromptProfileCatalog` | Exact catalog version, ordered profiles, source revision, review metadata and zero-authority status metadata |
| `PromptRenderInput` | Explicit canonical values needed by one render; no implicit clock, environment, catalog lookup or Provider default |
| `PromptRenderReceipt` | Process-only binding of one exact input, one exact snapshot, one renderer version and the exact Prompt bytes |
| `CatalogDigestReceipt` | Process-only binding of source bytes, canonical catalog projection and every non-Receipt generated artifact byte digest |

Unknown fields, duplicate identities, unknown taxonomy values, invalid placeholders, ambiguous
ordering, non-canonical text and inconsistent digests fail closed.

### 4. Approval, recommendation and selection are separate

An Agent may recommend one or more profile identities with reasons. A recommendation is advisory
authoring input only. It cannot select a Compiler profile, mutate a snapshot, authorize a Provider,
reserve an Attempt or initiate execution.

A human decision or separately approved deterministic policy must pin this exact triple:

```text
profile_id
profile_version
profile_sha256
```

The catalog identity must also be explicit. The renderer accepts no `latest`, default profile,
fallback profile, fuzzy match, keyword inference or run-time replacement. The exact triple must
resolve to exactly one entry under the supplied `catalog_version + catalog_sha256`, or rendering
fails before producing Prompt bytes.

Provider/model selection is outside profile selection. Runtime must never switch a profile,
template, Provider or model based on availability, price, retry state or free-form Agent output.

### 5. Rendering is a pure byte-level operation

The Phase 1 renderer consumes only an explicit `PromptRenderInput` and an admitted
`VisualPromptProfileSnapshot`. It performs no filesystem discovery, network I/O, Provider call,
credential read, clock read, randomness, UUID generation, localization lookup or mutable global
configuration.

The semantic input projection can contain these already-declared shot concepts when explicitly
supplied:

```text
narrative
visual direction
action
shot size
camera angle
camera movement
character asset bindings
scene asset binding
emotion by character
wardrobe by character
props
continuity notes
dialogue in source ordinal order
```

`PromptRenderInput` does not embed the Snapshot. The renderer receives the Input and Snapshot as two
exact values, and `PromptRenderReceipt` directly binds both identities.

Profile section order and literal delimiters are fixed by the profile version. Mappings are rendered
in ascending canonical key order. Character bindings use ascending `character_id`; dialogue uses its
explicit source ordinal; already ordered semantic tuples retain their admitted order. No locale or
insertion order may influence output.

Every admitted string must already be trimmed where required, NFC-normalized and free of forbidden
control characters. The renderer does not silently repair semantic input. Prompt output uses UTF-8,
NFC text, LF separators, no BOM, no trailing horizontal whitespace and exactly one terminal LF. The
same input projection, profile snapshot and renderer version must match the frozen byte-level known
answer for every conforming implementation; insertion order, locale and host OS are not semantic
inputs.

Phase 1 does not connect this renderer to the production Compiler. A later Compiler-integration
slice must prove how a Snapshot and Receipt close over compiled output, either through an external
immutable sidecar or an append-only contract version. This ADR does not presume that replacing the
existing `prompt` string is sufficient or that no contract change will be needed. Any integration
must update all affected identity, idempotency and golden-output tests.

## Phase 1 applicability and exact boundary

Phase 1 is limited to:

- one SDC-authored structured profile source;
- internal frozen validation and value types that are not released Pydantic contracts;
- exact lookup by `profile_id + profile_version + profile_sha256` under one exact catalog identity;
- a pure deterministic Prompt renderer and process-only render receipt;
- deterministic profile, input, catalog and receipt digest calculation;
- generated operator reference, Agent authoring reference and golden fixtures;
- a generated Catalog Digest Receipt and generated-artifact freshness check; and
- offline unit and repository-invariant tests.

Phase 1 adds no production call site to Compiler, Runtime or Provider paths. It creates no image
candidate, performs no qualification or asset promotion, and consumes no external community Prompt
or image.

## Frozen compatibility boundary

Phase 1 must not change:

- `StoryInput`, NIR, PIR, `AudioMasterClock`, `JobGraph` or `AssemblyPlan`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible`,
  `CharacterAssetBinding`, `StoryboardShotV2` or `GenerationJob`;
- the current production Compiler Prompt path or any compiled-artifact identity;
- Temporal/PostgreSQL ownership or durable workflow state;
- Provider `submit / inspect / download / cancel` semantics;
- persisted remote task IDs or `SUBMISSION_UNKNOWN -> HUMAN_GATE`;
- one current candidate, no more than two Creative Attempts or `STOP-2`;
- Provider authorization, entitlement, capability, pricing, credential or cost gates;
- `qc.verify` technical PASS/FAIL behavior or semantic QC's advisory-only status;
- any released Pydantic contract or committed JSON Schema byte; or
- `sdc.schemas.MODELS`, which remains exactly 68.

No prior ADR is amended retroactively. The fresh-status v3.0 evidence and Receipt path remains
untouched.

## Single structured source and generated artifacts

The source document has a fixed `catalog_version`, a bounded ordered profile collection and explicit
catalog review metadata. Each source profile uses a unique `(profile_id, profile_version)` and does
not contain `profile_sha256`. Strict admission derives that value from the complete source semantic
projection. `VisualPromptProfileSnapshot`, the generated Python catalog and Catalog Digest Receipt
carry the derived digest. Profiles are sorted by identity in canonical catalog projections;
duplicate IDs or versions are rejected rather than resolved by last-write wins.

`source_revision` is explicit reviewed provenance metadata. It is never populated from mutable
`HEAD` or inferred from the current working tree. The external source-assessment revision is not a
profile source revision and grants no rights to use external Prompt content.

Generic `approved_by` and `approved_at` fields are rejected because they imply broader approval than
this catalog can grant. Phase 1 instead uses the portable identifier `catalog_reviewer_ref` and
`catalog_reviewed_at`. `HUMAN_REVIEWED_FOR_OFFLINE_RENDER` requires both. The review instant is
explicit canonical UTC-second input; no generator or renderer reads the wall clock. These values
enter the catalog projection and catalog digest, but not the semantic profile hash or rendered
Prompt. They never appear in a compiled artifact, and their presence grants no Rights,
Qualification, Provider, Runtime or publication authority.

The Catalog Digest Receipt binds:

- the exact raw source-file SHA-256;
- the canonical catalog SHA-256;
- the ordered `(profile_id, profile_version, profile_sha256)` set;
- the generator and renderer format versions; and
- each non-Receipt generated artifact's path identity, raw byte SHA-256 and byte length in canonical
  order.

`CatalogDigestReceipt.generated_artifacts` binds every generated artifact except the Receipt
document itself. It never includes its own path, raw-byte SHA-256 or byte length. Its semantic digest
excludes only `catalog_digest_receipt_sha256`; freshness verification reconstructs the Receipt and
requires exact canonical-document byte equality. It contains no generated-at timestamp,
working-directory path, host name, user name, random value or implicit Git state.

## Profile taxonomy

The catalog uses independent typed axes. No axis is encoded as an unstructured combined tag.

| Axis | Meaning | Initial examples or rule |
| --- | --- | --- |
| asset purpose | Why a Prompt or reference is being produced | narrative shot, character identity, pose, expression, scene establishing, lighting, material or prop placement |
| visual style | First-party visual treatment identity | one controlled style ID; never inferred from keywords |
| narrative context | Story function represented by the image | dialogue, action, establishing, transition or other bounded first-party values |
| shot type | Image/shot construction role | narrative frame, reference sheet or other bounded structural value |
| reference asset type | Exact evidence/reference role | the character and scene role literals defined below |
| provider compatibility | `provider_syntax_compatibility_observations`: ordered static diagnostics | `UNASSESSED`, `SYNTAX_COMPATIBLE` or `INCOMPATIBLE` for one exact Provider profile |
| qualification status | `offline_render_admission_status`: profile-render admission only | `DRAFT`, `HUMAN_REVIEWED_FOR_OFFLINE_RENDER` or `RETIRED` |
| rights status | `profile_text_provenance_status`: profile-text provenance/review only | `FIRST_PARTY_TEXT_REVIEWED`, `RIGHTS_REVIEW_REQUIRED` or `PROHIBITED_EXTERNAL_CONTENT` |

`offline_render_admission_status` is about admission of profile text to this offline renderer. It is
not human Qualification of an image Candidate or asset. `profile_text_provenance_status` describes
only cataloged Prompt text and its reviewed source; it does not establish rights in a generated
output, reference asset, likeness, trademark or publication use.

The first five axes in the table enter the profile semantic projection. The final three are typed
catalog-entry metadata and enter only the catalog projection; they remain independent dimensions
even though they do not change `profile_sha256`.

Each provider-syntax observation binds exact `provider_id`, `provider_profile_id`,
`provider_profile_version` and `compatibility_status` values. Observations use canonical tuple order
and are never live capability or availability evidence.

Display labels and translated descriptions are presentation data. A display-label change must not
change the semantic profile projection, profile hash or Prompt bytes.

## Deterministic selection and Prompt rendering

The complete control flow is:

```text
Agent recommendation (optional, advisory)
    -> human or separately approved Policy decision
    -> exact profile_id + profile_version + profile_sha256
    -> exact catalog_version + catalog_sha256 admission
    -> immutable VisualPromptProfileSnapshot
    -> explicit PromptRenderInput
    -> pure renderer
    -> exact UTF-8 Prompt bytes + PromptRenderReceipt
```

Only the pinned identity enters rendering. Recommendation order, confidence, wording and Agent model
must not enter the Prompt projection. Catalog iteration order must not act as selection. A missing,
retired, ambiguous, hash-mismatched or non-admitted profile fails closed.

The renderer uses an allowlist of placeholders. Every placeholder must be known to the renderer
version, supplied exactly once by the input projection and valid for the profile's asset purpose.
Unused semantic fields, unknown placeholders and repeated placeholders are rejected unless the
profile version explicitly permits a fixed repetition. Template evaluation, arbitrary formatting
expressions and nested substitution are prohibited.

## Domain-separated hashes and canonical bytes

Semantic hashes align with the colon-separated, NUL-terminated v3.0 state-evidence convention.
This ADR freezes exactly these domain-prefix bytes for the five Phase 1 semantic digests; use of the
first three remains reserved until their field-level projections are approved as specified below:

```python
b"sdc:visual-prompt-profile:v1\0"
b"sdc:visual-prompt-catalog:v1\0"
b"sdc:visual-prompt-render-input:v1\0"
b"sdc:visual-prompt-render-receipt:v1\0"
b"sdc:visual-prompt-catalog-digest-receipt:v1\0"
```

Any additional semantic digest requires a separately specified unique domain and explicit review.
It must not reuse or extend these prefixes in place.

| Digest field | Projection boundary | Self-exclusion |
| --- | --- | --- |
| `profile_sha256` | Full field-level `VisualPromptProfile` projection to be frozen by the Phase 1 BUILD; it must include identity and every render-semantic field and exclude catalog/review/status and display metadata | Excludes every derived digest |
| `catalog_sha256` | Full field-level catalog projection to be frozen by the Phase 1 BUILD; it must include catalog/source review metadata, complete zero-authority state and ordered profile references plus entry metadata | Excludes `catalog_sha256` |
| `render_input_sha256` | Full field-level `PromptRenderInput` projection to be frozen by the Phase 1 BUILD | Excludes `render_input_sha256` |
| `prompt_render_receipt_sha256` | Every exact `PromptRenderReceipt` field listed below | Excludes `prompt_render_receipt_sha256` |
| `catalog_digest_receipt_sha256` | Every exact `CatalogDigestReceipt` field listed below | Excludes `catalog_digest_receipt_sha256` |

The object table above is an architectural minimum, not a field-level hash projection. Before
implementing the first three digests, the separately reviewed Phase 1 BUILD must enumerate their
exact JSON keys, nesting, scalar types, tuple order, literals, bounds and exclusions. Until that
field-level projection manifest is approved, the first three domain prefixes are reserved and no
digest made with them is a valid ADR-039 digest. No implementation may fill gaps by serializing an
incidental dataclass layout.

No digest may include itself directly or transitively. The profile projection must not include
catalog metadata; the catalog digest may then close over derived profile digests without a cycle.

The semantic digest rule is:

```text
lowercase_hex_sha256(domain_prefix || canonical_compact_json(exact_closed_projection))
```

`canonical_compact_json` is the UTF-8 encoding of the exact closed JSON projection serialized with
`allow_nan=False`, `ensure_ascii=False`, `separators=(",", ":")` and `sort_keys=True`. It has no
BOM, indentation, insignificant whitespace, CR or trailing LF. Every string and object key must
already be NFC and is rejected rather than normalized or repaired. Duplicate keys, non-finite
numbers, scalar coercion and non-canonical array order fail closed. Array order remains semantic and
is never automatically sorted unless its field definition requires canonical sorting.

Raw byte checksums remain deliberately different:

- `prompt_sha256` hashes the exact rendered Prompt bytes with no semantic domain prefix;
- source-file SHA-256 hashes the exact source bytes;
- generated-artifact SHA-256 hashes each exact generated file's bytes; and
- image/content SHA-256, in any future slice, hashes exact media bytes.

A field addition, field removal, semantic reinterpretation, projection change, ordering change,
codec change or domain change requires an explicit new version/domain and new golden fixtures. An
implementation must never silently recompute old identities under new semantics.

`profile_sha256`, `catalog_sha256`, `render_input_sha256`, `prompt_render_receipt_sha256` and
`catalog_digest_receipt_sha256` name domain-separated semantic projections. `prompt_sha256`,
source-document SHA-256 and generated-file SHA-256 name raw exact-byte digests. Implementations must
not use the two categories interchangeably. The existing Compiler `stable_id` helper is not a
substitute for these full 64-hex domain-separated digests; any optional short human handle must
retain and bind the complete semantic digest.

## PromptRenderReceipt and CatalogDigestReceipt

`PromptRenderReceipt` records only that one exact admitted render input and one exact profile
snapshot produced exact Prompt bytes under a fixed renderer. Its exact fields, in canonical JSON-key
spelling, are:

```text
receipt_purpose
profile_id
profile_version
profile_sha256
catalog_version
catalog_sha256
render_input_sha256
renderer_id
renderer_version
prompt_sha256
prompt_size_bytes
current_gate
provider_state
generation_authorized
execution_authorized
publication_authorized
remote_processing_allowed
retention_allowed
training_allowed
publication_allowed
automated_execution_allowed
authorized_attempts
authorized_cost_cny
posts_allowed
provider_requests
usage_restriction
grants_rights
grants_qualification
grants_execution_authority
eligible_for_asset_promotion
replaces_rights_manifest
prompt_render_receipt_sha256
```

The receipt contains no clock or environment-derived value.

`CatalogDigestReceipt` records only deterministic source-to-generated-artifact freshness. Its exact
fields are:

```text
receipt_purpose
source_path
source_sha256
source_size_bytes
catalog_version
catalog_sha256
profile_refs
generator_id
generator_version
renderer_id
renderer_version
generated_artifacts
reviewed_known_answer_path
reviewed_known_answer_sha256
reviewed_known_answer_size_bytes
current_gate
provider_state
generation_authorized
execution_authorized
publication_authorized
remote_processing_allowed
retention_allowed
training_allowed
publication_allowed
automated_execution_allowed
authorized_attempts
authorized_cost_cny
posts_allowed
provider_requests
usage_restriction
grants_rights
grants_qualification
grants_execution_authority
eligible_for_asset_promotion
replaces_rights_manifest
catalog_digest_receipt_sha256
```

`profile_refs` items have exactly `profile_id`, `profile_version` and `profile_sha256`.
`generated_artifacts` items have exactly `artifact_path`, `artifact_sha256` and
`artifact_size_bytes`. The latter tuple includes only generator-rebuildable artifacts, excludes the
Receipt itself and uses canonical ascending `artifact_path` order. The separately reviewed
known-answer vector is bound only by the three dedicated `reviewed_known_answer_*` fields.

All `*_sha256` values in both Receipts are exactly 64 lowercase hexadecimal characters. All byte
sizes are strict non-negative JSON integers, with `prompt_size_bytes > 0`; booleans and zero counters
are exact JSON scalar types and reject coercion. `profile_version`, `catalog_version`,
`renderer_version` and `generator_version` are canonical three-component numeric version strings
without leading zeros. IDs use the repository's portable-ID alphabet. Paths use the portable path
codec specified above. Tuple values serialize as JSON arrays in their admitted order. Missing,
unknown, null or type-coerced fields fail closed.

The Catalog Receipt has the same non-authoritative effect as the Prompt Receipt. Neither is a
released rights, Qualification or execution contract in Phase 1.

Each `PromptRenderReceipt` directly carries:

```text
receipt_purpose=DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY
```

Each `CatalogDigestReceipt` directly carries:

```text
receipt_purpose=CATALOG_SOURCE_AND_GENERATED_ARTIFACT_FRESHNESS_EVIDENCE_ONLY
```

Both Receipt types directly carry the complete common zero-authority field set:

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
grants_rights=false
grants_qualification=false
grants_execution_authority=false
eligible_for_asset_promotion=false
replaces_rights_manifest=false
```

Receipt construction, strict in-memory reconstruction, hash validity, catalog freshness or
successful re-rendering changes none of these values. A receipt does not prove that a negative
constraint was achieved, a QC expectation was met, an image is compliant, source content is
truthful, rights are current, a Candidate is qualified, a Provider is available or any action is
authorized. It never substitutes for the formal Rights Manifest path.

Phase 1 defines no runtime Receipt document parser, general filesystem reader or persistence API.
Only the deterministic build generator writes the exact generated paths declared above.

## Character reference asset flow

Profiles may define these exact character reference roles:

```text
CHARACTER_IDENTITY_SHEET
CHARACTER_POSE_REFERENCE
CHARACTER_EXPRESSION_REFERENCE
```

A cataloged `ReferenceAssetRecipe` is reusable semantic guidance and never contains a story-specific
`CharacterBible` identity. It declares these separate ordered constraints:

- face identity anchors;
- hairstyle anchors;
- wardrobe anchors;
- body proportion anchors;
- expression range;
- forbidden identity, hair, wardrobe and proportion drift;
- sheet layout and background requirements; and
- the required primary-asset binding fields.

`PromptRenderInput`, not the Recipe, binds the exact `CharacterBible`, active asset identity and
applicable shot values. The Receipt then closes over that Input and the reusable Snapshot.

The conceptual route is:

```text
CharacterBible
    -> admitted ReferenceAssetRecipe and ProfileSnapshot
    -> Prompt bytes and process-only Receipt
    -> [PHASE 1 ENDS]
    -> Candidate evidence only under another separately authorized boundary
    -> [BLOCKED FOR AI CANDIDATES UNTIL A SEPARATE
        PROVENANCE / QUALIFICATION ADR IS ACCEPTED]
    -> future eligible asset contract
```

Prompt rendering does not create a Candidate. Under the current contracts, an AI-generated
Candidate cannot complete the final transition; the provenance boundary below is blocking.

The current single active primary asset remains authoritative. Phase 1 freezes only the reference
role literals, their canonical order and their use in `ReferenceAssetRecipe`. It creates no
Candidate-sidecar or AssetVersion-sidecar record, additional active `CharacterAssetVersion` or
change to `CharacterAssetBinding`.

## Scene reference asset flow

Profiles may define these exact scene reference roles:

```text
SCENE_ESTABLISHING_REFERENCE
SCENE_LIGHTING_REFERENCE
SCENE_MATERIAL_REFERENCE
SCENE_PROP_PLACEMENT_REFERENCE
```

A cataloged scene look-development Recipe is reusable and does not contain a story-specific
`SceneBible` identity. It independently declares layout, geography, lighting, palette, material,
prop-placement, continuity, forbidden-drift and required primary-binding fields.
`PromptRenderInput` binds the exact `SceneBible` and active asset identity. The conceptual route is:

```text
SceneBible
    -> admitted scene ReferenceAssetRecipe and ProfileSnapshot
    -> Prompt bytes and process-only Receipt
    -> [PHASE 1 ENDS]
    -> Candidate evidence only under another separately authorized boundary
    -> [BLOCKED FOR AI CANDIDATES UNTIL A SEPARATE
        PROVENANCE / QUALIFICATION ADR IS ACCEPTED]
    -> future eligible asset contract
```

The current single active primary scene asset remains authoritative. Phase 1 freezes only the scene
role literals, their canonical order and their use in the Recipe. It creates no Candidate-sidecar,
AssetVersion-sidecar, additional active `SceneAssetVersion`, `StoryboardShotV2` change or Provider
input binding.

## Rights, qualification, provenance and Provider-authority boundary

These statements are independent and must never be collapsed:

| Item | What may be recorded | What is not granted |
| --- | --- | --- |
| External repository code/docs | MIT license observed at the fixed revision | Ownership or commercial clearance of collected community Prompts/images |
| External community Prompt | Source observation only | Import, adaptation or commercial use in SDC |
| External community image | Source observation only | Asset intake, training, publication or commercial use |
| SDC-authored profile | First-party text provenance and offline render review | Provider execution or rights in a generated output |
| SDC-generated reference Candidate | Future generation provenance and process evidence | Qualification, asset status, likeness/trademark clearance or commercial rights |
| Human-qualified AssetVersion | Qualification under an exact approved policy | A substitute for a current formal Rights Manifest |
| Commercial-use rights state | Formal rights evidence and review closure | Provider capability or execution authority |

`MaterialSourceRecord` remains a minimized source record, not a rights approval. Human
Qualification remains separate from Rights Manifest closure. Offline profile-render review remains
separate from both.

Catalog concepts named qualification, rights and compatibility are represented only by
`offline_render_admission_status`, `profile_text_provenance_status` and
`provider_syntax_compatibility_observations`. They are closed descriptive or offline
render-admission metadata. They grant no Provider capability, entitlement, credential, execution
permission, commercial-use right, publication permission or asset-promotion authority.

Provider compatibility records an observation about exact syntax/features under an exact reviewed
Provider/profile version. It cannot choose a Provider, enable an adapter, create fallback behavior or
override the Provider catalog and existing worker gates.

Offline rendering is admitted only when both of these exact states hold:

```text
offline_render_admission_status=HUMAN_REVIEWED_FOR_OFFLINE_RENDER
profile_text_provenance_status=FIRST_PARTY_TEXT_REVIEWED
```

`DRAFT`, `RETIRED`, `RIGHTS_REVIEW_REQUIRED` and `PROHIBITED_EXTERNAL_CONTENT` all fail closed.
Provider-syntax compatibility never grants render admission or authority.

## Zero-authority boundary

The `PromptProfileCatalog` top level directly carries this exact state:

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
```

Every catalog entry directly carries this exact catalog-metadata state:

```text
grants_rights=false
grants_qualification=false
grants_execution_authority=false
eligible_for_asset_promotion=false
```

Catalog authority values are never inherited implicitly from an enclosing object. Entry authority
metadata is excluded from the `VisualPromptProfile` semantic projection and included in the catalog
projection. The two Receipt types directly carry their own complete zero-authority values as
specified above.

Catalog admission, offline profile review, compatibility status, hash validity, render success and
freshness verification cannot change these states. `grants_rights=false` means the catalog grants no
rights; it does not make an external claim that no rights exist. All zero-authority values are
semantic projection inputs, not documentation comments.

## Guidance, pitfalls and QC boundary

Every profile keeps three ordered categories separate:

1. Positive Prompt Constraints describe content or treatment requested from a future generator.
2. Negative Prompt Constraints describe content or drift the Prompt asks a future generator to
   avoid.
3. QC Expectations describe possible later observations for an evaluator.

Negative Prompt Constraints are not QC facts and their presence is not evidence of satisfaction.
QC Expectations do not call or modify `qc.verify`. Semantic QC remains advisory-only and cannot
produce a technical failure, reserve an Attempt, retry a Provider request, promote an asset or
authorize publication.

Retry, Creative Attempt 2, `STOP-2` and `HUMAN_GATE` remain controlled solely by existing Policy.
The profile catalog and renderer contain no retry or recovery logic.

## Validation

The Phase 1 BUILD must pass the existing offline `make check`. Tests must cover at least:

- strict single-source validation, bounded sizes and unknown-field rejection;
- exact unique profile identities and fail-closed full-triple lookup;
- rejection of `latest`, default, fallback, keyword and Agent-output selection;
- canonical map, profile, recipe and role ordering independent of insertion order and locale;
- exact-path source loading with no current-directory search, environment override or fallback;
- persistent canonical source-document bytes and portable generated-artifact path identities;
- NFC/control-character admission and exact UTF-8/LF/no-BOM Prompt bytes;
- byte-identical rendering across repeated processes and agreement with reviewed known-answer
  vectors for every conforming implementation;
- generated golden Prompt bytes, raw `prompt_sha256` values and an independently reviewed
  known-answer vector that ordinary regeneration cannot rewrite;
- domain-separated profile, catalog, render-input and receipt hashes;
- an explicitly reviewed field-level projection manifest before the reserved profile, catalog or
  render-input domains are used, with no incidental dataclass serialization;
- exact Receipt field names, scalar types, nested item shapes, literals and self-field exclusions;
- proof that any render-semantic projection change requires a new version/domain;
- stable Catalog Digest Receipt and generated-artifact freshness failure on drift;
- proof that Catalog Digest Receipt never lists or hashes itself;
- immutable receipt and catalog zero-authority fields;
- proof that render success does not assert negative-constraint or QC success;
- exact offline-render admission predicate and proof that catalog status cannot authorize a
  Provider or asset promotion;
- fixed `ReferenceAssetRecipe` role order and proof that Phase 1 creates no sidecar, additional
  active asset binding or Provider input-material binding;
- proof that an AI-generated Candidate cannot be relabeled under current
  `IMPORTED_APPROVED_MEDIA` provenance;
- current Compiler output and deterministic identity regressions remaining unchanged;
- every committed Schema byte remaining unchanged and `sdc.schemas.MODELS` remaining exactly 68;
  and
- static/offline safety: no network, Provider POST, credential, paid-service or remote-generation
  call.

The repository must contain no imported external community Prompt, example image, dependency,
submodule, vendored source or installed external Agent Skill.

## Permitted claims and explicit non-proofs

After successful Phase 1 validation, SDC may claim only that:

- an exact first-party catalog projection has an exact semantic digest;
- one exact admitted input and Profile Snapshot deterministically produced exact Prompt bytes;
- a generated reference/document/fixture set matches its exact structured source; and
- profile selection, rendering and receipts remain offline and zero-authority.

It may not claim that:

- Prompt content is optimal, complete or suitable for every Provider;
- an Agent recommendation is approved or authoritative;
- a positive or negative constraint is present in an output image;
- a QC expectation passed;
- a generated Candidate is an approved AssetVersion;
- provenance, Qualification or Rights Manifest closure exists for an output;
- commercial, likeness, trademark, privacy, training or publication rights are granted;
- a Provider is capable, available, entitled, affordable or authorized; or
- generation, execution, publication, retention, training or spending is permitted.

## Rejected imports and designs

This ADR explicitly rejects:

- importing all 532 external examples;
- copying or lightly rewriting community Prompt text;
- copying external example images;
- adding the external repository as a dependency, submodule or vendored source;
- installing or invoking its npm package, plugin or Agent Skill;
- using keywords or substring matches as the final Compiler classifier;
- allowing an Agent to select or replace a profile at runtime;
- treating a catalog entry or API-key presence as Provider authority;
- directly adopting `api/generate-image.js` or its fixed Provider/model/credit semantics;
- replacing SDC's asynchronous Provider Runtime with a synchronous image POST;
- automatically promoting a successfully generated reference into an `AssetVersion`;
- relabeling generated media as `IMPORTED_APPROVED_MEDIA`;
- changing the current 68 formal Schemas for ADR-039 Phase 1;
- modifying the current Compiler Prompt path in Phase 1;
- treating a negative Prompt constraint as a QC fact; and
- appending this decision to SDC-ADR-038 or its merged change.

## Blocking follow-up boundaries

### Generated-reference Candidate provenance

Under the currently released contracts, an AI-generated reference Candidate must not be represented
as, relabeled as or promoted into `CharacterAssetVersion` or `SceneAssetVersion`. Downloading the
generated bytes, obtaining human review or re-importing the file does not make the existing
`IMPORTED_APPROVED_MEDIA` provenance literal a truthful representation of its origin.

This is a permanent fail-closed rule for the current contract versions, not a permanent product
prohibition. A separately reviewed provenance and Qualification ADR may later introduce an
append-only generated-Candidate contract and promotion path. That ADR must define generation
provenance, Provider Attempt/task evidence, profile and receipt binding, content hashes, human
Qualification, Rights Manifest integration, retention/privacy, revocation and migration semantics.
ADR-039 grants no advance approval for that work.

ADR-039 does not create, authorize creation of, ingest, store, retain, upload or process a Candidate.
If a generated Candidate exists under another separately authorized boundary, ADR-039 treats it
only as non-authoritative evidence and makes it ineligible for asset promotion until the separate
ADR is accepted and implemented.

### Multiple reference roles

ADR-039 preserves one active primary asset binding. It selects one primary asset plus a typed
sidecar as the default future design direction, but Phase 1 defines no sidecar contract or API. A
separate ADR must define both the pre-promotion Candidate-evidence closure and the post-promotion
AssetVersion-bound closure; those lifecycle states must not be conflated. Any future sidecar cannot
replace or mutate the primary `AssetVersion`, change the Storyboard binding, or grant execution or
rights authority.

If an approved Provider route later requires multiple role-specific images to be submitted
simultaneously, a separate ADR must define an append-only V2 binding or Provider input-material
contract, deterministic role ordering, persistence, rights closure, size/count limits and
idempotency impact. Existing `AssetVersion` contracts must not be extended or reinterpreted in
place.

These two issues block candidate promotion and multi-reference Provider execution, respectively.
They do not block preparation and separate review of the Phase 1 offline BUILD.

## Risk disposition

| Severity | Risk | Required treatment |
| --- | --- | --- |
| Blocking for later execution, not Phase 1 | Truthful provenance and Qualification closure for an AI-generated Candidate | Keep promotion fail closed; require the separate provenance and Qualification ADR above |
| Blocking for later execution, not Phase 1 | Simultaneous multi-role reference inputs to a Provider | Keep primary asset plus typed sidecar as the future direction; require a separate lifecycle and append-only binding/Provider-input ADR |
| Important for Phase 1 | Receipt or catalog status being mistaken for authorization, rights or compliance | Encode and test immutable zero-authority fields and explicit non-proofs |
| Important for Phase 1 | Semantic and raw-byte digests being mixed or silently reinterpreted | Freeze exact domains, projections, codecs, field names and version-bump rules |
| Important for Phase 1 | Generated views drifting from the structured source | Generate deterministically and fail freshness checks on any byte drift |
| Important for Phase 1 | First-party profiles accidentally incorporating external community content | Require source review and prohibit imported Prompt/image content |
| Deferred semantic / Important | Reusing `AssetVersion.visual_description` in rendering | Require versioned projection, identity-impact review and new golden fixtures |
| Minor / Phase 2 | Label localization and presentation-only catalog views | Keep outside semantic projections and Prompt bytes |

## Phase 2 deferred work

The following presentation improvements are Minor and may follow Phase 1:

- display-label internationalization; and
- operator-facing grouping, filtering and presentation refinements that do not enter semantic
  projections.

Reusing `AssetVersion.visual_description` as a render input is not a cosmetic Minor change. It
changes Prompt semantics and, whenever the rendered Prompt bytes differ, deterministically changes
`StoryboardShotV2` identity, `GenerationJob` identity/idempotency and downstream compiled-artifact
identities. It requires an explicitly versioned render/profile contract, a new digest/domain where
applicable, refreshed golden fixtures and compatibility tests.

Compiler integration, generated-Candidate provenance, remote generation, multi-reference Provider
execution, Qualification, AssetVersion promotion and any Rights Manifest integration are separate
reviewed BUILD/ADR slices, not Phase 2 presentation optimizations.

## Consequences

Positive consequences:

- profile selection and Prompt bytes become deterministically replayable against exact evidence;
- a single source plus freshness checks makes byte drift among runtime, operator and Agent views
  detectable;
- profile recommendation, selection, rendering, Qualification, rights and execution stay visibly
  separate;
- all released contracts and the exact 68-Schema boundary remain intact in Phase 1; and
- generated-candidate provenance and multi-reference execution receive explicit future review
  gates.

Costs and limitations:

- Phase 1 produces no image asset and authorizes no generation;
- AI-generated Candidates remain ineligible for promotion until a separate provenance ADR closes;
- simultaneous multi-reference Provider execution remains unavailable;
- the selected future sidecar direction still requires separate lifecycle and closure design;
- every render-semantic change requires a new version/domain and refreshed golden fixtures; and
- some description duplication remains until a separately versioned semantic-reuse design is
  accepted.
