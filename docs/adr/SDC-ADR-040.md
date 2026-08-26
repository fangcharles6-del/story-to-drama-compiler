# SDC-ADR-040: Visual Prompt Profiles Phase 1 Projection Manifest

- Status: Proposed
- Date: 2026-08-26
- Depends on: SDC-ADR-039 / Deterministic Visual Prompt Profiles
- Baseline: `af255151bed510237da6a48fa77281faca39bbb9`
- Authority: `HUMAN_GATE / NOT_AUTHORIZED`
- Data boundary: repository-owned first-party text and deterministic local process evidence only
- Network/spend boundary: zero network calls, zero credentials, zero Provider requests

## Context

SDC-ADR-039 accepts the architecture for an offline, first-party visual Prompt profile catalog. It
also deliberately reserves the profile, catalog and render-input hash domains until a separately
reviewed Phase 1 BUILD enumerates the exact closed projections. The accepted ADR does not freeze the
complete source JSON shape, the first four taxonomy enums, the `PromptRenderInput` nested items, the
reference-recipe union, renderer grammar or the required bounds.

Those omissions are intentional safety gates. Filling them from an incidental dataclass layout
would make an implementation-specific serialization look like an approved semantic identity.
Implementing the three reserved digests before the field-level manifest is accepted would therefore
produce values that are not valid ADR-039 digests.

This ADR is that field-level manifest. It closes the Phase 1 format decisions needed before code is
written. While its status is `Proposed`, all three reserved domains remain unusable. Acceptance
permits a separately reviewed Phase 1 implementation against this exact manifest; acceptance does
not itself assert that source data, generated artifacts, known-answer vectors or valid digests
exist.

This ADR does not connect visual Prompt profiles to the Compiler, Runtime, Provider, Candidate,
Qualification, AssetVersion promotion or Rights Manifest paths. It creates no execution authority.

## Decision summary

Phase 1 will use:

- one strict package-relative JSON source;
- internal frozen and slotted value objects;
- three explicit closed semantic projections, never incidental object serialization;
- one fixed renderer grammar with no expression evaluator;
- one manually reviewed known-answer document that ordinary generation cannot rewrite;
- one deterministic generator with mutually exclusive check and update modes; and
- exact raw-byte freshness over every generated artifact except the Catalog Digest Receipt itself.

All names, types, enum values, nullability, bounds, ordering and exclusions below are normative.
An implementation must reject any value outside them rather than normalize, coerce, infer, sort or
repair it unless this ADR explicitly says otherwise.

## Frozen compatibility boundary

This manifest and its future Phase 1 implementation must not change:

- `StoryInput`, NIR, PIR, `AudioMasterClock`, `JobGraph` or `AssemblyPlan`;
- `CharacterAssetVersion`, `CharacterBible`, `SceneAssetVersion`, `SceneBible`,
  `CharacterAssetBinding`, `StoryboardShotV2` or `GenerationJob`;
- the current Compiler Prompt path or any compiled-artifact identity;
- Temporal/PostgreSQL ownership, workflow state or migrations;
- Provider `submit / inspect / download / cancel` behavior;
- persisted task IDs, `SUBMISSION_UNKNOWN -> HUMAN_GATE`, Attempt limits or `STOP-2`;
- Provider authority, entitlement, capability, pricing, credentials or cost gates;
- `qc.verify` technical PASS/FAIL behavior or semantic QC's advisory-only status;
- any released Pydantic contract or committed JSON Schema byte; or
- `sdc.schemas.MODELS`, which remains exactly 68.

No prior ADR is amended retroactively. The fresh-status v3.0 evidence chain and Receipt codecs
remain untouched.

## Common scalar codecs

### Exact built-in scalar types

Admission checks exact built-in types. A JSON boolean is not an integer; `0.0`, `"0"`, `false` and
subclass instances are not the integer `0`. No scalar coercion is permitted.

The following codecs are frozen:

| Codec | Exact rule |
| --- | --- |
| `PortableId` | JSON string matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` |
| `ProviderId` | JSON string matching `^[a-z][a-z0-9._-]{0,63}$` |
| `SemanticVersion` | three dot-separated decimal components; no leading zero unless the component is `0`; each component uses at most 10 digits and is at most `2147483647` |
| `LowerSha256` | JSON string matching `^[0-9a-f]{64}$` |
| `UtcSecond` | real calendar instant in exact `YYYY-MM-DDTHH:MM:SSZ` form; no offset, fraction or leap second |
| `CanonicalText` | exact NFC JSON string with no Unicode `Cc`, `Cs`, `Zl` or `Zp` code point |
| `TrimmedText` | `CanonicalText` equal to its own `strip()` result |
| `StrictNonNegativeInt` | exact JSON integer in `0..9223372036854775807` |
| `PortablePath` | NFC repository-relative path using `/`, as constrained below |

The exact `SemanticVersion` regular expression is
`^(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})\.(0|[1-9][0-9]{0,9})$`; admission additionally
enforces the component bound after numeric parsing.

All text and path length limits count Unicode scalar values after NFC validation. UTF-8 byte limits
are separately named as byte limits. `TrimmedText` means that neither end contains a code point from
this frozen set:

```text
U+0009..U+000D, U+0020, U+0085, U+00A0, U+1680,
U+2000..U+200A, U+2028, U+2029, U+202F, U+205F, U+3000
```

Several members are already rejected by `CanonicalText`; listing the complete end-trim set prevents
language-runtime `strip()` or Unicode-version behavior from defining admission.

`PortablePath` has total length `1..512`, every segment has length `1..128`, and no segment is
empty, `.` or `..`. A path must not begin with `/`, `\\`, a drive prefix, or contain `\\`, NUL, `:`
in its first segment, or any control/surrogate code point. Its only separator is `/`.

All semantic text fields are single-line because controls, surrogates and Unicode line/paragraph
separators, including CR, LF and TAB, are rejected. Semantic text fields do not permit empty strings;
only explicitly bounded structured collections may be empty.

`PromptText` is the sole multiline text codec. Its UTF-8 bytes must satisfy the renderer output
rules: NFC, LF only, no BOM, no trailing horizontal whitespace, no empty terminal line beyond the
required terminator, exactly one terminal LF and total size `1..65536` bytes.

### Global admission bounds

Phase 1 freezes these limits:

| Item | Limit |
| --- | ---: |
| source JSON bytes | 262144 |
| known-answer JSON bytes | 262144 |
| Receipt JSON bytes | 262144 |
| JSON nesting depth | 16 |
| catalog entries | 1..64 |
| compatibility observations per entry | 0..32 |
| sections per profile | 1..16 |
| constraints in each constraint category | 1..32 |
| items in each recipe field | 1..16 |
| Prompt output bytes | 1..65536 |
| generated artifacts | 1..256 |
| known-answer cases | exactly 3 in v1 |

Limits are measured before expensive traversal where possible. A value at the limit is admitted; a
value above it fails closed.

JSON container depth counts the root object as depth 1. Entering an object or array increments depth
by one; scalar members do not add another level. No admitted document may contain a container at a
depth greater than 16.

## Closed taxonomy values and canonical order

The first four taxonomy axes use these complete Phase 1 enum sets:

```text
AssetPurpose:
  NARRATIVE_SHOT
  CHARACTER_REFERENCE_ASSET
  SCENE_REFERENCE_ASSET

VisualStyleId:
  sdc.cinematic-storyboard.v1

NarrativeContext, in canonical tuple order:
  DIALOGUE
  ACTION
  ESTABLISHING
  TRANSITION
  REFERENCE_DEVELOPMENT

ShotType:
  NARRATIVE_FRAME
  REFERENCE_SHEET
```

The three shot/camera fields freeze these complete v1 literal snapshots. Admission does not query
future enum membership from `contracts.py`:

```text
ShotSizeV1:
  EXTREME_CLOSE_UP
  CLOSE_UP
  MEDIUM_CLOSE_UP
  MEDIUM
  MEDIUM_WIDE
  WIDE
  EXTREME_WIDE

CameraAngleV1:
  EYE_LEVEL
  LOW_ANGLE
  HIGH_ANGLE
  DUTCH_ANGLE
  OVERHEAD
  POV

CameraMovementV1:
  STATIC
  PAN
  TILT
  DOLLY
  TRUCK
  PEDESTAL
  HANDHELD
  CRANE
  ZOOM
  ORBIT
```

These values equal the current contract enums at the named baseline. A later addition to a released
contract enum does not expand the ADR-040 v1 input domain.

Reference-asset roles use this one complete canonical order:

```text
CHARACTER_IDENTITY_SHEET
CHARACTER_POSE_REFERENCE
CHARACTER_EXPRESSION_REFERENCE
SCENE_ESTABLISHING_REFERENCE
SCENE_LIGHTING_REFERENCE
SCENE_MATERIAL_REFERENCE
SCENE_PROP_PLACEMENT_REFERENCE
```

The existing ADR-039 catalog metadata literals remain exact:

```text
OfflineRenderAdmissionStatus:
  DRAFT
  HUMAN_REVIEWED_FOR_OFFLINE_RENDER
  RETIRED

ProfileTextProvenanceStatus:
  FIRST_PARTY_TEXT_REVIEWED
  RIGHTS_REVIEW_REQUIRED
  PROHIBITED_EXTERNAL_CONTENT

ProviderSyntaxCompatibilityStatus:
  UNASSESSED
  SYNTAX_COMPATIBLE
  INCOMPATIBLE
```

Only the exact pair
`HUMAN_REVIEWED_FOR_OFFLINE_RENDER + FIRST_PARTY_TEXT_REVIEWED` admits offline rendering.
Compatibility status never participates in admission or authority.

## PromptConstraintSet projection

The complete projection is:

```json
{
  "negative_prompt_constraints": ["TrimmedText(1..1000)", "..."],
  "positive_prompt_constraints": ["TrimmedText(1..1000)", "..."],
  "qc_expectations": ["TrimmedText(1..1000)", "..."]
}
```

Each array contains `1..32` unique items. Array order is authored semantic order and is never
sorted.
The three arrays remain independent. Positive and negative constraints are rendered using the
grammar below. QC expectations are bound by `profile_sha256` but never emitted into Prompt bytes and
never become QC facts.

## ReferenceAssetRecipe tagged union

Within `VisualPromptProfile` and the two recipe shapes, `reference_asset_recipe` is either JSON
`null` or exactly one of the two shapes below. No other field in those shapes is nullable.

### CharacterReferenceAssetRecipe

```json
{
  "background_requirements": ["TrimmedText(1..1000)", "..."],
  "body_proportion_anchors": ["TrimmedText(1..1000)", "..."],
  "expression_range": ["TrimmedText(1..1000)", "..."],
  "face_identity_anchors": ["TrimmedText(1..1000)", "..."],
  "forbidden_body_proportion_drift": ["TrimmedText(1..1000)", "..."],
  "forbidden_hairstyle_drift": ["TrimmedText(1..1000)", "..."],
  "forbidden_identity_drift": ["TrimmedText(1..1000)", "..."],
  "forbidden_wardrobe_drift": ["TrimmedText(1..1000)", "..."],
  "hairstyle_anchors": ["TrimmedText(1..1000)", "..."],
  "recipe_kind": "CHARACTER_REFERENCE",
  "reference_asset_types": [
    "CHARACTER_IDENTITY_SHEET",
    "CHARACTER_POSE_REFERENCE",
    "CHARACTER_EXPRESSION_REFERENCE"
  ],
  "required_primary_binding_fields": [
    "character_id",
    "asset_version_id",
    "asset_content_sha256"
  ],
  "sheet_layout_requirements": ["TrimmedText(1..1000)", "..."],
  "wardrobe_anchors": ["TrimmedText(1..1000)", "..."]
}
```

Every guidance array contains `1..16` unique items and preserves authored order.
`reference_asset_types` is a non-empty unique subset of the three character roles in their frozen
canonical order. `required_primary_binding_fields` equals the shown three-element array exactly.

### SceneReferenceAssetRecipe

```json
{
  "continuity_requirements": ["TrimmedText(1..1000)", "..."],
  "forbidden_drift": ["TrimmedText(1..1000)", "..."],
  "geography_anchors": ["TrimmedText(1..1000)", "..."],
  "layout_requirements": ["TrimmedText(1..1000)", "..."],
  "lighting_anchors": ["TrimmedText(1..1000)", "..."],
  "material_anchors": ["TrimmedText(1..1000)", "..."],
  "palette_anchors": ["TrimmedText(1..1000)", "..."],
  "prop_placement_anchors": ["TrimmedText(1..1000)", "..."],
  "recipe_kind": "SCENE_REFERENCE",
  "reference_asset_types": [
    "SCENE_ESTABLISHING_REFERENCE",
    "SCENE_LIGHTING_REFERENCE",
    "SCENE_MATERIAL_REFERENCE",
    "SCENE_PROP_PLACEMENT_REFERENCE"
  ],
  "required_primary_binding_fields": [
    "scene_id",
    "asset_version_id",
    "asset_content_sha256"
  ]
}
```

Every guidance array contains `1..16` unique items and preserves authored order.
`reference_asset_types` is a non-empty unique subset of the four scene roles in their frozen
canonical order. `required_primary_binding_fields` equals the shown three-element array exactly.

A character recipe cannot contain a scene role, and a scene recipe cannot contain a character role.
Recipes contain no story-specific Bible ID, Candidate ID, Provider input, sidecar or asset-promotion
state.

## Section descriptor and placeholder allowlist

Each section descriptor has exactly these fields:

```json
{
  "heading": "TrimmedText(1..80)",
  "placeholder": "one exact PlaceholderId",
  "section_id": "PortableId"
}
```

`heading` must not contain `{`, `}`, or `:`. `section_id`, `heading` and `placeholder` are each
unique within a profile. Phase 1 permits no repeated placeholder.

The complete placeholder allowlist and order is:

```text
narrative
visual_direction
action
shot_size
camera_angle
camera_movement
character_asset_bindings
scene_asset_binding
emotion_by_character
wardrobe_by_character
props
continuity_notes
dialogue
```

The required placeholder set is exact for each asset purpose, although the profile's section array
may arrange that set in its authored semantic order:

| Asset purpose | Exact placeholder set |
| --- | --- |
| `NARRATIVE_SHOT` | all thirteen placeholders |
| `CHARACTER_REFERENCE_ASSET` | `narrative`, `visual_direction`, `action`, `character_asset_bindings`, `emotion_by_character`, `wardrobe_by_character`, `continuity_notes` |
| `SCENE_REFERENCE_ASSET` | `narrative`, `visual_direction`, `action`, `scene_asset_binding`, `props`, `continuity_notes` |

There is no template string, brace substitution, expression language, condition, nested expansion,
callback or arbitrary formatter. A section selects exactly one typed input field.

## VisualPromptProfile closed projection

The complete profile projection, and therefore the exact input to the profile domain hash, is:

```json
{
  "asset_purpose": "AssetPurpose",
  "constraint_set": {
    "negative_prompt_constraints": ["..."],
    "positive_prompt_constraints": ["..."],
    "qc_expectations": ["..."]
  },
  "narrative_contexts": ["NarrativeContext", "..."],
  "profile_id": "PortableId",
  "profile_version": "SemanticVersion",
  "reference_asset_recipe": null,
  "reference_asset_types": [],
  "renderer_version": "SemanticVersion",
  "sections": [
    {
      "heading": "TrimmedText(1..80)",
      "placeholder": "PlaceholderId",
      "section_id": "PortableId"
    }
  ],
  "shot_type": "ShotType",
  "visual_style_id": "VisualStyleId"
}
```

The keys above are exhaustive. `profile_sha256`, catalog entry status, review metadata,
compatibility observations, zero-authority values, display data and all other digests are excluded.

`narrative_contexts` contains `1..5` unique values in the frozen canonical order. The sections array
contains `1..16` items, preserves authored order and has the exact purpose-specific placeholder set.

Cross-field closure is exact:

- `NARRATIVE_SHOT` uses `NARRATIVE_FRAME`, has an empty `reference_asset_types` array and a null
  recipe;
- `CHARACTER_REFERENCE_ASSET` uses `REFERENCE_SHEET`, contains only character roles, and has a
  character recipe with exactly the same role array;
- `SCENE_REFERENCE_ASSET` uses `REFERENCE_SHEET`, contains only scene roles, and has a scene recipe
  with exactly the same role array;
- reference profiles include `REFERENCE_DEVELOPMENT` in `narrative_contexts` and narrative profiles
  do not; and
- `renderer_version` equals the enclosing source document's renderer version.

Any semantic field change requires a new `profile_version`. In known-answer v1, an ordinary source
change under an existing pair changes `profile_sha256`, breaks the frozen known-answer fingerprint
closure and makes both check and update fail. The current-document loader validates only the current
document and does not falsely claim access to immutable repository history. A coordinated manual
edit of source, known answer and its authored fingerprint is visible review input; governance must
reject it unless the profile version also changes. This is a review rule, not a cryptographic claim
that a clean checkout can discover every historical value.

The hash rule is exactly:

```text
sha256(
  b"sdc:visual-prompt-profile:v1\0"
  || canonical_compact_json(the exact object above)
).hexdigest()
```

No dataclass walk, `asdict`, `__dict__`, Pydantic dump or generic object serializer may define this
projection.

## Catalog source document

The only source path is exactly:

```text
src/sdc/visual_prompt_profiles.json
```

The source root has exactly these fields:

```json
{
  "automated_execution_allowed": false,
  "authorized_attempts": 0,
  "authorized_cost_cny": 0,
  "catalog_reviewer_ref": "PortableId",
  "catalog_reviewed_at": "UtcSecond",
  "catalog_version": "SemanticVersion",
  "current_gate": "HUMAN_GATE",
  "execution_authorized": false,
  "generation_authorized": false,
  "posts_allowed": 0,
  "profiles": [],
  "provider_requests": 0,
  "provider_state": "NOT_AUTHORIZED",
  "publication_allowed": false,
  "publication_authorized": false,
  "remote_processing_allowed": false,
  "renderer_id": "sdc.visual-prompt-renderer",
  "renderer_version": "1.0.0",
  "retention_allowed": false,
  "source_revision": "PortableId",
  "training_allowed": false,
  "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
}
```

`profiles` contains `1..64` source entries in ascending `(profile_id, numeric profile_version)`
order. The loader rejects a non-canonical order; it does not sort it. A pair is unique. The same
`profile_id` may have multiple versions and different profiles may share a version.

Each source entry has exactly:

```json
{
  "description": "TrimmedText(1..1000)",
  "display_name": "TrimmedText(1..128)",
  "eligible_for_asset_promotion": false,
  "grants_execution_authority": false,
  "grants_qualification": false,
  "grants_rights": false,
  "offline_render_admission_status": "OfflineRenderAdmissionStatus",
  "profile": {},
  "profile_text_provenance_status": "ProfileTextProvenanceStatus",
  "provider_syntax_compatibility_observations": []
}
```

`profile` is the complete `VisualPromptProfile` projection above and does not contain
`profile_sha256`. Display fields and all remaining source-entry fields are catalog metadata.

Each provider observation has exactly:

```json
{
  "compatibility_status": "ProviderSyntaxCompatibilityStatus",
  "provider_id": "ProviderId",
  "provider_profile_id": "PortableId",
  "provider_profile_version": "PortableId"
}
```

Observations are unique by `(provider_id, provider_profile_id, provider_profile_version)` and must
already be sorted by that tuple using Unicode code-point order. Provider profile versions are opaque
reviewed identifiers, not SDC semantic versions. The status is not part of the uniqueness key.

The initial Phase 1 source contains exactly these three profile identities, each at version
`1.0.0`, in the shown source order:

```text
sdc.character-reference.cinematic.v1
sdc.narrative-shot.cinematic.v1
sdc.scene-reference.cinematic.v1
```

They use `sdc.cinematic-storyboard.v1` and respectively cover
`CHARACTER_REFERENCE_ASSET`, `NARRATIVE_SHOT` and `SCENE_REFERENCE_ASSET`. The character profile
contains all three character roles; the scene profile contains all four scene roles. Initial
provider-syntax observation arrays are empty so that the catalog makes no Provider compatibility
claim. A future catalog version may add profiles within the `1..64` format bound, but it cannot
rewrite these identities at `1.0.0` with different profile semantics. Adding an admitted profile
also requires a separately reviewed known-answer version, case-set manifest and generator version;
known-answer v1 remains the exact three-case closure below.

The three entries may be staged as `DRAFT` while their first-party text is under review. The
implementation cannot finalize known-answer renders until the exact text is explicitly accepted and
the entries are changed to the sole admitted status/provenance pair. That review remains limited to
offline rendering and grants no other authority.

`catalog_reviewer_ref` and `catalog_reviewed_at` are always mandatory explicit source values.
`HUMAN_REVIEWED_FOR_OFFLINE_RENDER` may be asserted only when those exact values identify the human
review boundary that reviewed the entry. A loader or generator never fills either value from a
clock, environment, user account or Git state. The future BUILD must not claim first-party review
for Prompt text that has not been explicitly reviewed in that BUILD.

## PromptProfileCatalog closed projection

After deriving each `profile_sha256`, the catalog hash projection is exactly:

```json
{
  "automated_execution_allowed": false,
  "authorized_attempts": 0,
  "authorized_cost_cny": 0,
  "catalog_reviewer_ref": "PortableId",
  "catalog_reviewed_at": "UtcSecond",
  "catalog_version": "SemanticVersion",
  "current_gate": "HUMAN_GATE",
  "execution_authorized": false,
  "generation_authorized": false,
  "posts_allowed": 0,
  "profile_entries": [
    {
      "description": "TrimmedText(1..1000)",
      "display_name": "TrimmedText(1..128)",
      "eligible_for_asset_promotion": false,
      "grants_execution_authority": false,
      "grants_qualification": false,
      "grants_rights": false,
      "offline_render_admission_status": "OfflineRenderAdmissionStatus",
      "profile_ref": {
        "profile_id": "PortableId",
        "profile_sha256": "LowerSha256",
        "profile_version": "SemanticVersion"
      },
      "profile_text_provenance_status": "ProfileTextProvenanceStatus",
      "provider_syntax_compatibility_observations": []
    }
  ],
  "provider_requests": 0,
  "provider_state": "NOT_AUTHORIZED",
  "publication_allowed": false,
  "publication_authorized": false,
  "remote_processing_allowed": false,
  "renderer_id": "sdc.visual-prompt-renderer",
  "renderer_version": "1.0.0",
  "retention_allowed": false,
  "source_revision": "PortableId",
  "training_allowed": false,
  "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
}
```

The keys and nesting above are exhaustive. `catalog_sha256`, source path, raw source hash and size,
generator identity, known-answer identity, generated artifacts and complete profile bodies are
excluded. Each `profile_ref` binds its profile body through `profile_sha256` without creating a
cycle. Entry order is the validated source entry order and includes every `DRAFT`, render-admitted
and `RETIRED` entry; status never filters the catalog hash projection.

The hash rule is exactly:

```text
sha256(
  b"sdc:visual-prompt-catalog:v1\0"
  || canonical_compact_json(the exact object above)
).hexdigest()
```

## VisualPromptProfileSnapshot

The Snapshot is a flattened immutable value: every `VisualPromptProfile` projection key occurs once,
followed logically by exactly these three derived catalog-binding fields:

```text
profile_sha256: LowerSha256
catalog_version: SemanticVersion
catalog_sha256: LowerSha256
```

`profile_id` and `profile_version` are not duplicated outside the flattened profile fields. Internal
Python composition may retain a nested profile object, but any explicit snapshot projection or
comparison follows the flattened definition and never an incidental object layout.

The resolver requires the caller to supply all five identity values:

```text
catalog_version
catalog_sha256
profile_id
profile_version
profile_sha256
```

It must find exactly one matching entry and verify both digests before constructing a Snapshot. It
fails before rendering on missing, ambiguous, retired, draft, provenance-blocked or hash-mismatched
content. It accepts no `latest`, aliases, defaults, fallback, keyword selection, catalog iteration
selection or Agent free text.

## PromptRenderInput nested items

### CharacterAssetPromptBinding

```json
{
  "asset_content_sha256": "LowerSha256",
  "asset_version_id": "PortableId",
  "character_id": "PortableId"
}
```

The tuple contains `0..2` bindings, already sorted by `character_id`. Character IDs and asset
version IDs are each unique. The values are caller-asserted references to one primary asset
identity. The renderer can bind and hash them but cannot prove that they currently occur in a Bible.
They do not create a new active binding or reuse `AssetVersion.visual_description`.

### SceneAssetPromptBinding

```json
{
  "asset_content_sha256": "LowerSha256",
  "asset_version_id": "PortableId",
  "scene_id": "PortableId"
}
```

There is at most one scene binding. Its values are caller-asserted references to the primary scene
asset identity, not proof of current Bible state, a sidecar or a Provider multi-input binding.

### DialoguePromptLine

```json
{
  "character_id": "PortableId",
  "line_id": "PortableId",
  "ordinal": 0,
  "text": "TrimmedText(1..2000)"
}
```

The tuple contains `0..64` lines with unique `line_id` and unique `StrictNonNegativeInt` `ordinal`.
It must already be in strictly ascending ordinal order. The renderer never sorts it. Every dialogue
`character_id` must occur in the character binding tuple.

## PromptRenderInput closed tagged union

`PromptRenderInput` is exactly one of three tagged projections. A variant contains no field that its
profile does not use. The Input is independently valid and hashable. `input_kind` must equal the
Snapshot's `asset_purpose`; mismatch fails before producing Prompt bytes or a Receipt.

### NarrativeShotPromptRenderInput

```json
{
  "action": "TrimmedText(1..2000)",
  "camera_angle": "CameraAngleV1",
  "camera_movement": "CameraMovementV1",
  "character_asset_bindings": [],
  "continuity_notes": "TrimmedText(1..2000)",
  "dialogue": [],
  "emotion_by_character": {},
  "input_kind": "NARRATIVE_SHOT",
  "narrative": "TrimmedText(1..4000)",
  "props": [],
  "scene_asset_binding": {},
  "shot_size": "ShotSizeV1",
  "visual_direction": "TrimmedText(1..4000)",
  "wardrobe_by_character": {}
}
```

`character_asset_bindings` contains `0..2` exact items. Emotion and wardrobe objects each have the
same exact key set as those bindings and values of `TrimmedText(1..512)`. `dialogue` contains
`0..64` items. `props` contains `0..16` unique `TrimmedText(1..128)` values already in Unicode
code-point order. A narrative shot with no characters has empty bindings, emotion, wardrobe and
dialogue. The scene binding and all scalar fields are required.

### CharacterReferencePromptRenderInput

```json
{
  "action": "TrimmedText(1..2000)",
  "character_asset_bindings": [{}],
  "continuity_notes": "TrimmedText(1..2000)",
  "emotion_by_character": {},
  "input_kind": "CHARACTER_REFERENCE_ASSET",
  "narrative": "TrimmedText(1..4000)",
  "visual_direction": "TrimmedText(1..4000)",
  "wardrobe_by_character": {}
}
```

The binding array contains exactly one item for the one `CharacterBible` flow. Emotion and wardrobe
objects each contain exactly that `character_id` key and one `TrimmedText(1..512)` value. This
projection has no scene, shot/camera, prop or dialogue field.

### SceneReferencePromptRenderInput

```json
{
  "action": "TrimmedText(1..2000)",
  "continuity_notes": "TrimmedText(1..2000)",
  "input_kind": "SCENE_REFERENCE_ASSET",
  "narrative": "TrimmedText(1..4000)",
  "props": [],
  "scene_asset_binding": {},
  "visual_direction": "TrimmedText(1..4000)"
}
```

The scene binding and every scalar field are required. `props` contains `0..16` unique
`TrimmedText(1..128)` values already in Unicode code-point order. This projection has no character,
emotion, wardrobe, shot/camera or dialogue field.

The keys of each variant are exhaustive. There is no Snapshot, digest, clock, environment,
Provider, model, locale, policy, recommendation or execution field. Objects are represented
internally by immutable tuples of entries in ascending key order; no caller-owned mutable mapping
is retained. Missing, unknown or cross-variant fields fail closed instead of being represented by
empty/null sentinels.

The render-input hash rule is exactly:

```text
sha256(
  b"sdc:visual-prompt-render-input:v1\0"
  || canonical_compact_json(the exact object above)
).hexdigest()
```

## Canonical compact JSON

All five semantic digests use the ADR-039 codec exactly:

```text
UTF-8
allow_nan=false
ensure_ascii=false
separators=(",", ":")
sort_keys=true
no BOM
no CR
no indentation or insignificant whitespace
no terminal LF
```

Every string and object key must already be NFC. Arrays preserve their admitted semantic order.
Only fields whose rules explicitly require a canonical order are checked against that order; the
implementation does not silently sort source semantic arrays.

## Frozen renderer identity and grammar

The initial renderer identity is:

```text
renderer_id=sdc.visual-prompt-renderer
renderer_version=1.0.0
```

The renderer receives only one admitted `PromptRenderInput` and one separately resolved Snapshot.
It reads no source file, generated file, current directory, environment, clock, randomness, UUID,
locale, network, credential, Provider or mutable global configuration.

For every section, it writes exactly:

```text
<heading><ASCII COLON><ASCII SPACE><rendered value><LF>
```

Scalar text and enum values render as their exact admitted string. Structured values render as the
same compact canonical JSON used above, decoded as UTF-8. An empty array or object renders as `[]`
or `{}`. No quoting, escaping or repair is applied to scalar text because embedded controls were
already rejected.

After the final input section, the renderer writes exactly:

```text
Positive Prompt Constraints:<LF>
- <positive item 1><LF>
...
Negative Prompt Constraints:<LF>
- <negative item 1><LF>
...
```

If the profile has a reference recipe, the renderer then writes `Reference Asset Recipe:<LF>` and
the following fixed lines in exactly the listed order. Every recipe array is rendered as compact
canonical JSON.

Character recipe order:

```text
Recipe kind
Reference asset types
Face identity anchors
Hairstyle anchors
Wardrobe anchors
Body proportion anchors
Expression range
Forbidden identity drift
Forbidden hairstyle drift
Forbidden wardrobe drift
Forbidden body proportion drift
Sheet layout requirements
Background requirements
Required primary binding fields
```

Scene recipe order:

```text
Recipe kind
Reference asset types
Layout requirements
Geography anchors
Lighting anchors
Palette anchors
Material anchors
Prop placement anchors
Continuity requirements
Forbidden drift
Required primary binding fields
```

Each recipe line uses the same `<label>: <value><LF>` syntax. There are no blank lines. The output
is NFC UTF-8 without BOM, has LF only, has no trailing horizontal whitespace and has exactly one
terminal LF. Output outside `1..65536` bytes fails before returning a Prompt or Receipt.

QC expectations are deliberately not written. Their presence in the Snapshot and profile digest is
not evidence that any expectation passed. Renderer success does not assert that a positive or
negative constraint was achieved in an image.

## PromptRenderReceipt projection

The Receipt fields, literals and zero-authority state remain exactly those frozen by ADR-039. The
semantic projection contains every field below except `prompt_render_receipt_sha256` itself:

```text
receipt_purpose=DETERMINISTIC_PROMPT_RENDER_PROCESS_EVIDENCE_ONLY
profile_id: PortableId
profile_version: SemanticVersion
profile_sha256: LowerSha256
catalog_version: SemanticVersion
catalog_sha256: LowerSha256
render_input_sha256: LowerSha256
renderer_id=sdc.visual-prompt-renderer
renderer_version=1.0.0
prompt_sha256: LowerSha256
prompt_size_bytes: exact integer in 1..65536
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

`prompt_sha256` is raw SHA-256 over the exact Prompt bytes and has no domain. The receipt digest is:

```text
sha256(
  b"sdc:visual-prompt-render-receipt:v1\0"
  || canonical_compact_json(the exact fields above)
).hexdigest()
```

The final Receipt adds `prompt_render_receipt_sha256` and no other field. The Receipt contains
neither the Prompt text nor the render input payload, and it contains no time or environment value.

## Persistent canonical documents

The authoritative source, known-answer document, generated Prompt Render Receipts and Catalog
Digest Receipt use:

```text
UTF-8 without BOM
all strings and keys already NFC
recursive key sorting
two-space indentation
ensure_ascii=false
allow_nan=false
LF only
exactly one terminal LF
```

Admission rejects malformed UTF-8, duplicate keys, BOM, CR, non-finite numbers, floats, unknown or
missing keys, type coercion, excess depth, excess size, non-NFC text and bytes that differ from
exact re-encoding. It never returns a repaired document.

Other generated text, including Python, Markdown and Prompt fixtures, uses UTF-8 without BOM, NFC,
LF, no trailing horizontal whitespace and exactly one terminal LF.

## Known-answer document

The manually reviewed path is exactly:

```text
tests/fixtures/visual_prompt_profiles/reviewed-known-answer-v1.json
```

Its root has exactly:

```json
{
  "cases": [],
  "known_answer_version": "1.0.0"
}
```

`cases` contains exactly these three entries in this order:

```text
character-reference-basic
narrative-shot-unicode
scene-reference-basic
```

These are the complete `case_id` literal set for known-answer v1, not arbitrary `PortableId` values.
This prevents filename length, Windows reserved-name and case-folding ambiguity. Each case has
exactly:

```json
{
  "case_id": "one exact known-answer v1 case literal",
  "catalog_sha256": "LowerSha256",
  "catalog_version": "SemanticVersion",
  "profile_id": "PortableId",
  "profile_sha256": "LowerSha256",
  "profile_version": "SemanticVersion",
  "prompt_render_receipt": {},
  "prompt_sha256": "LowerSha256",
  "prompt_size_bytes": 1,
  "prompt_text": "PromptText",
  "render_input": {},
  "render_input_sha256": "LowerSha256"
}
```

`render_input` is the exact closed projection above. `prompt_render_receipt` is the complete
Receipt, including its self digest. All duplicated identities and sizes must agree exactly.
`prompt_text` uses the dedicated `PromptText` codec.
The example integer `1` denotes the field type and lower bound; the admitted
`prompt_size_bytes` is the exact computed integer in `1..65536`.

The character, narrative and scene cases resolve the correspondingly named initial profile. Together
they cover all three asset purposes, all seven reference roles, non-ASCII NFC text, empty permitted
collections and a narrative input with two characters and multiple source-ordered dialogue lines.

The authored generator module freezes the reviewed known-answer raw SHA-256 and byte length as
literal constants. Check and update both fail if either differs. Ordinary update has no code path
that writes, replaces, deletes, renames or reformats this document. Updating it requires a distinct
manual edit, independent byte review and an explicit change to both frozen fingerprint constants.

For each case, the generator follows only this derivation algorithm:

1. strictly parse the source and independently derive every profile digest and the catalog digest;
2. strictly parse the case input and derive its render-input digest;
3. resolve a Snapshot using the case's exact catalog and profile five-value identity;
4. call the production pure renderer and construct the production Prompt Render Receipt;
5. compare the recomputed input digest, Prompt text bytes, raw Prompt digest, byte size and complete
   Receipt bytes with every duplicated expected value in the known-answer case; and
6. only after all cases agree, use the recomputed Prompt and Receipt bytes as generated fixtures.

The generator never copies expected Prompt or Receipt values directly into generated fixtures.
Any disagreement fails before any update write. Tests also use an independent encoder and literal
domain prefixes so the production renderer and generator cannot validate the same defect by sharing
one erroneous helper.

## Generated view projections

`src/sdc/visual_prompt_catalog.py` exposes exactly one internal generated value named
`VISUAL_PROMPT_CATALOG`. It contains the complete validated source catalog, every full semantic
profile, every entry metadata field, every derived `profile_sha256` and the derived
`catalog_sha256`. It contains no source-file raw digest, known-answer value, Catalog Digest Receipt
or environment value. An independent test projects the generated object field by field and requires
exact equality with a fresh strict source build; importing the generated module is never how the
generator rebuilds it.

Both generated Markdown documents contain a machine-delimited canonical JSON block. The operator
reference block contains the complete catalog projection plus each full semantic profile. The Agent
authoring reference block contains the same profile identities, taxonomy, section descriptors,
constraints, recipes, catalog status and zero-authority metadata, preceded by a fixed statement that
recommendation is advisory and cannot select or execute a profile. Independent tests parse those
blocks and compare every field to the source-derived values; prose presence alone is insufficient.

Python and Markdown layout bytes are governed by `generator_version`. Any generator formatting or
view-projection change requires a new generator version and refreshed raw artifact digests, even
when profile and catalog semantic digests remain unchanged.

## Generated artifact closure

The initial generator identity is:

```text
generator_id=sdc.visual-prompt-profile-generator
generator_version=1.0.0
```

The complete non-Catalog-Receipt artifact allowlist, shown in the exact ascending Unicode code-point
order used by `generated_artifacts`, is:

```text
docs/reference/visual-prompt-agent-authoring.md
docs/reference/visual-prompt-profiles.md
src/sdc/visual_prompt_catalog.py
tests/fixtures/visual_prompt_profiles/generated/character-reference-basic.prompt-render-receipt.json
tests/fixtures/visual_prompt_profiles/generated/character-reference-basic.prompt.txt
tests/fixtures/visual_prompt_profiles/generated/narrative-shot-unicode.prompt-render-receipt.json
tests/fixtures/visual_prompt_profiles/generated/narrative-shot-unicode.prompt.txt
tests/fixtures/visual_prompt_profiles/generated/scene-reference-basic.prompt-render-receipt.json
tests/fixtures/visual_prompt_profiles/generated/scene-reference-basic.prompt.txt
```

The Catalog Digest Receipt path is fixed separately at
`docs/reference/visual-prompt-catalog-digest-receipt.json`. No other file is permitted in the
generated fixture directory. Known-answer v1 case identities cannot be added, removed or renamed;
a changed case set requires a separately reviewed known-answer and generator version.

`generated_artifacts` in the Catalog Digest Receipt includes the generated Python file, both
generated Markdown files, every generated Prompt fixture and every generated Prompt Render Receipt
fixture. The phrase “except the Receipt itself” in ADR-039 means only the Catalog Digest Receipt at
`docs/reference/visual-prompt-catalog-digest-receipt.json`. Generated Prompt Render Receipt fixtures
are included in the closure.

The known-answer document is excluded from `generated_artifacts` and bound only through its three
dedicated fields. The source document is also excluded from `generated_artifacts` and bound only
through its dedicated fields.

The generator must reject path aliasing, duplicates, symlinks and any path outside the exact
allowlist.

## CatalogDigestReceipt projection

The semantic projection contains every field below except `catalog_digest_receipt_sha256` itself:

```text
receipt_purpose=CATALOG_SOURCE_AND_GENERATED_ARTIFACT_FRESHNESS_EVIDENCE_ONLY
source_path=src/sdc/visual_prompt_profiles.json
source_sha256: raw LowerSha256
source_size_bytes: exact StrictNonNegativeInt
catalog_version: SemanticVersion
catalog_sha256: LowerSha256
profile_refs: ordered exact items
generator_id=sdc.visual-prompt-profile-generator
generator_version=1.0.0
renderer_id=sdc.visual-prompt-renderer
renderer_version=1.0.0
generated_artifacts: ordered exact items
reviewed_known_answer_path=tests/fixtures/visual_prompt_profiles/reviewed-known-answer-v1.json
reviewed_known_answer_sha256: raw LowerSha256
reviewed_known_answer_size_bytes: exact StrictNonNegativeInt
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

Each `profile_refs` item has exactly:

```json
{
  "profile_id": "PortableId",
  "profile_sha256": "LowerSha256",
  "profile_version": "SemanticVersion"
}
```

Profile references use the catalog entry order.

Each `generated_artifacts` item has exactly:

```json
{
  "artifact_path": "PortablePath",
  "artifact_sha256": "LowerSha256",
  "artifact_size_bytes": 0
}
```

Artifact hashes are raw byte SHA-256 values and byte sizes are exact non-negative integers. The
Phase 1 v1 has exactly nine `generated_artifacts` items in the frozen allowlist order. The Catalog
Digest Receipt never lists or hashes itself.

Its digest is:

```text
sha256(
  b"sdc:visual-prompt-catalog-digest-receipt:v1\0"
  || canonical_compact_json(the exact fields above)
).hexdigest()
```

The final persistent document adds `catalog_digest_receipt_sha256` and no other field.

## Source loading and generated catalog separation

The future implementation uses this module split:

```text
src/sdc/visual_prompt_profiles.py
  internal enums, frozen values, explicit projections, hashes, exact lookup and pure renderer

src/sdc/visual_prompt_profile_source.py
  exact package-relative source-byte reader and strict source parser

src/sdc/visual_prompt_profile_codegen.py
  pure artifact builder plus explicit check/update CLI

src/sdc/visual_prompt_catalog.py
  generated static catalog data only
```

Importing the runtime profile module or generated catalog must not read the source JSON. The
generator reads only `Path(__file__).with_name("visual_prompt_profiles.json")`; its production loader
accepts no path argument, current-directory search, environment override or fallback. Tests inject
bytes into a private parser rather than widening the production loader.

The source and reviewed-known-answer paths must each be a regular non-symlink file at the exact
frozen location. Readers enforce the size limit before reading, compare file identity and size
before and after reading, and reject replacement or mutation during the read. They never follow a
symlink to repository-external content.

For repository-only generated paths, codegen resolves the root as the third parent of its own
resolved module path (`Path(__file__).resolve().parents[2]`) and requires the expected `src/sdc`
layout plus a regular non-symlink `pyproject.toml` whose project name is
`story-to-drama-compiler`. It never searches ancestors, uses CWD or accepts a substitute root.
Portable receipt paths are fixed literals and never contain that absolute root.

The generated catalog contains static validated data and full derived digests. Runtime lookup uses
that generated catalog and does not parse a repository document. The generator does not import the
possibly stale generated catalog while rebuilding it.

Internal collection fields are tuples. Frozen objects retain no caller-owned list or dictionary.
Every semantic projection function lists keys explicitly. The implementation must not refactor
unrelated private canonical helpers into a shared framework as part of this slice.

## Generator commands and CI

The only generator modes are explicit and mutually exclusive:

```text
python -m sdc.visual_prompt_profile_codegen --check
python -m sdc.visual_prompt_profile_codegen --update
```

There is no default mode, path override, root override, environment configuration or cleanup mode.

`--check` performs no write, rename, delete, metadata update or timestamp touch. It constructs the
complete expected closure in memory and fails on a missing, extra, reordered or byte-different
artifact.

`--update` writes only the fixed generated allowlist. It never touches the source, known-answer,
Schema, Compiler fixture or any path outside the allowlist. It computes all non-Catalog-Receipt
artifacts in memory first and the Catalog Receipt last. An implementation should use replace-on-
success writes but must not expose a general filesystem writer as a runtime API.

Known-answer v1 has a fixed case set, so update never needs to delete a formerly valid case path.
An unexpected extra generated-directory entry makes both modes fail; neither mode deletes it.
Removing such an untracked or review-visible extra file is a separate explicit repository operation,
not an inferred cleanup side effect.

The Makefile adds `visual-prompt-profiles` for explicit update and
`visual-prompt-profiles-check` for check-only operation. `make check` includes the check target.
Because the existing CI invokes its phases separately, `.github/workflows/ci.yml` must also invoke
only `--check`; CI never invokes `--update`.

No new dependency is needed. Tests must verify that the JSON source is present in the built wheel.

## Cross-platform raw-byte preservation

Raw-byte digests make line-ending conversion semantic for the source and generated artifacts. The
repository currently permits platform Git settings to rewrite text line endings. The Phase 1 BUILD
must add path-scoped `.gitattributes` rules equivalent to:

```gitattributes
/src/sdc/visual_prompt_profiles.json text eol=lf
/src/sdc/visual_prompt_catalog.py text eol=lf
/docs/reference/visual-prompt-profiles.md text eol=lf
/docs/reference/visual-prompt-agent-authoring.md text eol=lf
/docs/reference/visual-prompt-catalog-digest-receipt.json text eol=lf
/tests/fixtures/visual_prompt_profiles/** text eol=lf
```

A fresh Windows checkout with `core.autocrlf=true` and a Linux checkout must expose identical bytes
for every path in the receipt closure. The generator still verifies bytes; `.gitattributes` is not a
substitute for admission or freshness checks.

CI adds one lightweight Windows job that installs the locked Python environment, runs
`visual-prompt-profiles-check` and runs only the visual Prompt profile test files. The existing Linux
job continues to run the complete suite. Cross-host consistency is claimed only when both jobs pass
the same reviewed known-answer bytes; changing the supported-host claim requires separate review.

## Validation matrix

The separately reviewed implementation must pass the existing offline `make check`. Tests must
cover at least:

- exact frozen/slotted deep immutability and absence of retained mutable collections;
- strict source and known-answer parsing, duplicate-key rejection, bounds and canonical bytes;
- the exact field sets, nesting, scalar types, enum values, nullability and exclusions in this ADR;
- independent known-answer calculations that do not call the production projection/hash helpers;
- mutation of every profile, catalog and input semantic field changing the expected digest;
- independent use of both literal Receipt domains and an independent canonical encoder, with every
  non-self Receipt field mutation changing the corresponding semantic digest;
- proof that raw Prompt/source/artifact hashes never use a semantic domain and semantic hashes never
  substitute for raw byte hashes;
- catalog/display/status fields being excluded from `profile_sha256` and included where specified
  in `catalog_sha256`;
- exact full-triple lookup under an exact catalog identity and rejection of all inferred selection;
- purpose/recipe/role/placeholder closure and fixed role order;
- character bindings sorted by `character_id`, maps by key and dialogue by supplied ordinal;
- repeated-process equality under different CWD, `PYTHONHASHSEED`, timezone, locale and host OS;
- exact Prompt grammar, Unicode NFC, LF, terminal newline, byte limit and raw digest;
- proof that QC expectations are not Prompt lines and negative constraints are not QC facts;
- Receipt exact fields, strict integer/boolean handling, self exclusions and zero authority;
- source-path isolation from CWD files and environment variables;
- check-mode failure on missing, extra, stale, reordered, BOM, CRLF or manually edited artifacts;
- update-mode inability to touch the known-answer document;
- a frozen independent known-answer raw fingerprint that update cannot re-bless;
- an unchanged-version source mutation failing against known-answer v1, with version changes exposed
  as explicit source and reviewed-known-answer diffs rather than silent repair;
- Catalog Receipt inclusion of Prompt Receipt fixtures and exclusion only of itself;
- exact 68-Schema path-and-byte baseline remaining unchanged;
- frozen v1 and Creative Sample v2 Compiler output/identity baselines remaining unchanged;
- package-data inclusion of `visual_prompt_profiles.json`;
- static and runtime denial of network, Provider, credential, clock, randomness and dynamic imports;
- proof that no Candidate, sidecar, additional active asset or Provider input binding is produced;
- proof that Phase 1 exposes no path from render/fixture evidence to an `AssetVersion`, never calls
  the `IMPORTED_APPROVED_MEDIA` provenance literal and makes no source-truth claim that current
  contracts cannot verify; and
- absence of imported external Prompt/image content, dependency, submodule, vendored source or
  installed external Agent Skill.

No new integration test or external service is required. Content originality and first-party review
remain human review facts and cannot be established by a keyword scan alone.

## Explicit non-proofs and rejected scope

Acceptance or implementation of this manifest cannot prove or grant:

- Prompt quality, Provider suitability or generation success;
- Agent selection authority;
- Provider capability, availability, entitlement, credential or execution permission;
- satisfaction of a positive or negative constraint;
- QC PASS, retry eligibility, Attempt 2 or recovery authority;
- Candidate provenance, Qualification or AssetVersion status;
- Rights Manifest closure, commercial rights or publication permission;
- retention, remote processing, training or spending permission; or
- Compiler integration or identity compatibility for a future changed Prompt.

This slice rejects:

- implementing any reserved domain while this ADR remains Proposed;
- filling a projection with incidental dataclass serialization;
- adding a Pydantic contract or changing the 68 Schemas;
- editing the Compiler Prompt function;
- adding runtime Receipt parsing, persistence or general path inputs;
- creating a Candidate, sidecar, new active asset or multi-reference Provider binding;
- reusing `AssetVersion.visual_description`;
- Provider/model fallback or Agent/keyword selection;
- any network, credential, paid-service or remote generation call; and
- any external community Prompt, image, template prose, dependency, submodule, vendored source,
  plugin or Agent Skill.

## Consequences

If accepted, the first three ADR-039 digest domains will have complete reviewed projections and may
be used only by a later Phase 1 implementation conforming to this manifest. Profile identity will
bind every profile semantic field, catalog identity will bind review/status/zero-authority metadata
through profile references, and render-input identity will bind one complete explicit input without
a Snapshot cycle.

The cost is deliberate rigidity: even a field, codec, ordering or renderer-grammar change requires
a new version/domain and reviewed known answers. The implementation must also manage raw-byte line
endings explicitly across Windows and Linux.

Until this ADR is Accepted and the separate implementation passes its full review, SDC must continue
to claim that no ADR-039 Phase 1 digest, catalog, renderer or Receipt implementation exists.
