# Visual Prompt Agent Authoring Reference

Recommendation is advisory only. An Agent cannot select a profile, trigger rendering, choose a Provider, initiate execution, or grant rights, qualification, publication, training, spending, or asset promotion.

<!-- SDC-VISUAL-PROMPT-AGENT-JSON:BEGIN -->
```json
{
  "catalog_projection": {
    "authorized_attempts": 0,
    "authorized_cost_cny": 0,
    "automated_execution_allowed": false,
    "catalog_reviewed_at": "2026-08-27T03:06:32Z",
    "catalog_reviewer_ref": "github.fangcharles6-del",
    "catalog_version": "1.0.0",
    "current_gate": "HUMAN_GATE",
    "execution_authorized": false,
    "generation_authorized": false,
    "posts_allowed": 0,
    "profile_entries": [
      {
        "description": "Offline deterministic character reference-sheet profile for identity, pose, and expression continuity.",
        "display_name": "Cinematic Character Reference",
        "eligible_for_asset_promotion": false,
        "grants_execution_authority": false,
        "grants_qualification": false,
        "grants_rights": false,
        "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
        "profile_ref": {
          "profile_id": "sdc.character-reference.cinematic.v1",
          "profile_sha256": "54901f50bc718eb6f51d866c842c70791c7d341e7f9c20c37281ee0bc840434d",
          "profile_version": "1.0.0"
        },
        "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
        "provider_syntax_compatibility_observations": []
      },
      {
        "description": "Offline deterministic cinematic storyboard profile for one narrative shot.",
        "display_name": "Cinematic Narrative Shot",
        "eligible_for_asset_promotion": false,
        "grants_execution_authority": false,
        "grants_qualification": false,
        "grants_rights": false,
        "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
        "profile_ref": {
          "profile_id": "sdc.narrative-shot.cinematic.v1",
          "profile_sha256": "3da25632ad7798921a88200c591cd8774b65e533b6dd54a35be4c96802365181",
          "profile_version": "1.0.0"
        },
        "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
        "provider_syntax_compatibility_observations": []
      },
      {
        "description": "Offline deterministic scene reference-sheet profile for layout, light, materials, and prop continuity.",
        "display_name": "Cinematic Scene Reference",
        "eligible_for_asset_promotion": false,
        "grants_execution_authority": false,
        "grants_qualification": false,
        "grants_rights": false,
        "offline_render_admission_status": "HUMAN_REVIEWED_FOR_OFFLINE_RENDER",
        "profile_ref": {
          "profile_id": "sdc.scene-reference.cinematic.v1",
          "profile_sha256": "ea62abd6c0f35da2fa2ccc0d79ecc5e629aed84f14378dce0e14d88f49f11b0d",
          "profile_version": "1.0.0"
        },
        "profile_text_provenance_status": "FIRST_PARTY_TEXT_REVIEWED",
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
    "source_revision": "sdc.visual-prompt-profiles.phase1-reviewed.1",
    "training_allowed": false,
    "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
  },
  "profiles": [
    {
      "asset_purpose": "CHARACTER_REFERENCE_ASSET",
      "constraint_set": {
        "negative_prompt_constraints": [
          "Do not add unrequested characters, garments, accessories, text, logos, or watermarks.",
          "Do not merge reference panels or alter the supplied character identity."
        ],
        "positive_prompt_constraints": [
          "Preserve the supplied character identity across every reference panel.",
          "Keep facial structure, hairstyle, wardrobe, and body proportions consistent.",
          "Present the requested reference views with clear production-readable separation."
        ],
        "qc_expectations": [
          "Every requested character reference role is visually inspectable.",
          "The same character identity remains consistent across all panels."
        ]
      },
      "narrative_contexts": [
        "REFERENCE_DEVELOPMENT"
      ],
      "profile_id": "sdc.character-reference.cinematic.v1",
      "profile_version": "1.0.0",
      "reference_asset_recipe": {
        "background_requirements": [
          "Use a clean neutral background with clear silhouette separation."
        ],
        "body_proportion_anchors": [
          "Preserve the supplied head-to-body ratio, build, limb length, and stance."
        ],
        "expression_range": [
          "Show a controlled range from neutral through focused, concerned, and joyful expressions."
        ],
        "face_identity_anchors": [
          "Preserve facial geometry, feature spacing, eye shape, nose shape, and jawline."
        ],
        "forbidden_body_proportion_drift": [
          "Do not change body scale, build, limb proportions, or apparent age."
        ],
        "forbidden_hairstyle_drift": [
          "Do not change hair length, silhouette, parting, texture, or color."
        ],
        "forbidden_identity_drift": [
          "Do not substitute, blend, beautify, age, or otherwise redesign the character identity."
        ],
        "forbidden_wardrobe_drift": [
          "Do not replace, simplify, recolor, or add unrequested wardrobe elements."
        ],
        "hairstyle_anchors": [
          "Preserve hair length, silhouette, parting, texture, and color."
        ],
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
        "sheet_layout_requirements": [
          "Arrange views in a legible reference-sheet grid with consistent scale and spacing."
        ],
        "wardrobe_anchors": [
          "Preserve garment silhouette, layering, palette, materials, and distinctive accessories."
        ]
      },
      "reference_asset_types": [
        "CHARACTER_IDENTITY_SHEET",
        "CHARACTER_POSE_REFERENCE",
        "CHARACTER_EXPRESSION_REFERENCE"
      ],
      "renderer_version": "1.0.0",
      "sections": [
        {
          "heading": "Character Context",
          "placeholder": "narrative",
          "section_id": "character-context"
        },
        {
          "heading": "Visual Direction",
          "placeholder": "visual_direction",
          "section_id": "character-visual-direction"
        },
        {
          "heading": "Reference Action",
          "placeholder": "action",
          "section_id": "character-reference-action"
        },
        {
          "heading": "Primary Character Binding",
          "placeholder": "character_asset_bindings",
          "section_id": "character-primary-binding"
        },
        {
          "heading": "Expression Direction",
          "placeholder": "emotion_by_character",
          "section_id": "character-expression-direction"
        },
        {
          "heading": "Wardrobe Direction",
          "placeholder": "wardrobe_by_character",
          "section_id": "character-wardrobe-direction"
        },
        {
          "heading": "Continuity Notes",
          "placeholder": "continuity_notes",
          "section_id": "character-continuity-notes"
        }
      ],
      "shot_type": "REFERENCE_SHEET",
      "visual_style_id": "sdc.cinematic-storyboard.v1"
    },
    {
      "asset_purpose": "NARRATIVE_SHOT",
      "constraint_set": {
        "negative_prompt_constraints": [
          "Do not introduce unbound characters, locations, props, text, logos, or watermarks.",
          "Do not contradict the supplied camera, wardrobe, emotion, or continuity values."
        ],
        "positive_prompt_constraints": [
          "Render one coherent cinematic storyboard frame from the supplied shot values.",
          "Preserve every supplied character and scene asset identity.",
          "Keep action, emotion, wardrobe, props, dialogue context, and continuity mutually consistent."
        ],
        "qc_expectations": [
          "The frame remains traceable to every supplied narrative and visual-direction value.",
          "Character, scene, wardrobe, prop, and camera continuity are visually inspectable."
        ]
      },
      "narrative_contexts": [
        "DIALOGUE",
        "ACTION",
        "ESTABLISHING",
        "TRANSITION"
      ],
      "profile_id": "sdc.narrative-shot.cinematic.v1",
      "profile_version": "1.0.0",
      "reference_asset_recipe": null,
      "reference_asset_types": [],
      "renderer_version": "1.0.0",
      "sections": [
        {
          "heading": "Narrative",
          "placeholder": "narrative",
          "section_id": "shot-narrative"
        },
        {
          "heading": "Visual Direction",
          "placeholder": "visual_direction",
          "section_id": "shot-visual-direction"
        },
        {
          "heading": "Action",
          "placeholder": "action",
          "section_id": "shot-action"
        },
        {
          "heading": "Shot Size",
          "placeholder": "shot_size",
          "section_id": "shot-size"
        },
        {
          "heading": "Camera Angle",
          "placeholder": "camera_angle",
          "section_id": "shot-camera-angle"
        },
        {
          "heading": "Camera Movement",
          "placeholder": "camera_movement",
          "section_id": "shot-camera-movement"
        },
        {
          "heading": "Character Asset Bindings",
          "placeholder": "character_asset_bindings",
          "section_id": "shot-character-bindings"
        },
        {
          "heading": "Scene Asset Binding",
          "placeholder": "scene_asset_binding",
          "section_id": "shot-scene-binding"
        },
        {
          "heading": "Emotion by Character",
          "placeholder": "emotion_by_character",
          "section_id": "shot-emotion"
        },
        {
          "heading": "Wardrobe by Character",
          "placeholder": "wardrobe_by_character",
          "section_id": "shot-wardrobe"
        },
        {
          "heading": "Props",
          "placeholder": "props",
          "section_id": "shot-props"
        },
        {
          "heading": "Continuity Notes",
          "placeholder": "continuity_notes",
          "section_id": "shot-continuity-notes"
        },
        {
          "heading": "Dialogue",
          "placeholder": "dialogue",
          "section_id": "shot-dialogue"
        }
      ],
      "shot_type": "NARRATIVE_FRAME",
      "visual_style_id": "sdc.cinematic-storyboard.v1"
    },
    {
      "asset_purpose": "SCENE_REFERENCE_ASSET",
      "constraint_set": {
        "negative_prompt_constraints": [
          "Do not add unrequested locations, structures, props, signage, text, logos, or watermarks.",
          "Do not change the supplied scene identity, geography, lighting logic, or material language."
        ],
        "positive_prompt_constraints": [
          "Preserve the supplied scene identity across every reference panel.",
          "Keep geography, layout, lighting, palette, materials, and prop placement mutually consistent.",
          "Present the requested scene references with clear production-readable separation."
        ],
        "qc_expectations": [
          "Every requested scene reference role is visually inspectable.",
          "Scene geography, light direction, materials, and prop placement remain consistent across panels."
        ]
      },
      "narrative_contexts": [
        "REFERENCE_DEVELOPMENT"
      ],
      "profile_id": "sdc.scene-reference.cinematic.v1",
      "profile_version": "1.0.0",
      "reference_asset_recipe": {
        "continuity_requirements": [
          "Preserve spatial relationships, light direction, material assignments, and prop positions across views."
        ],
        "forbidden_drift": [
          "Do not relocate architecture, reverse geography, change light direction, or replace anchored materials and props."
        ],
        "geography_anchors": [
          "Preserve entrances, exits, sight lines, elevation changes, and landmark relationships."
        ],
        "layout_requirements": [
          "Show a coherent establishing view and supporting references at consistent spatial scale."
        ],
        "lighting_anchors": [
          "Preserve key-light direction, softness, color temperature, contrast, and practical-light placement."
        ],
        "material_anchors": [
          "Preserve surface type, finish, wear, reflectivity, and texture scale."
        ],
        "palette_anchors": [
          "Preserve the dominant, supporting, and accent color relationships."
        ],
        "prop_placement_anchors": [
          "Preserve each named prop position, orientation, scale, and relationship to fixed landmarks."
        ],
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
      },
      "reference_asset_types": [
        "SCENE_ESTABLISHING_REFERENCE",
        "SCENE_LIGHTING_REFERENCE",
        "SCENE_MATERIAL_REFERENCE",
        "SCENE_PROP_PLACEMENT_REFERENCE"
      ],
      "renderer_version": "1.0.0",
      "sections": [
        {
          "heading": "Scene Context",
          "placeholder": "narrative",
          "section_id": "scene-context"
        },
        {
          "heading": "Visual Direction",
          "placeholder": "visual_direction",
          "section_id": "scene-visual-direction"
        },
        {
          "heading": "Reference Action",
          "placeholder": "action",
          "section_id": "scene-reference-action"
        },
        {
          "heading": "Primary Scene Binding",
          "placeholder": "scene_asset_binding",
          "section_id": "scene-primary-binding"
        },
        {
          "heading": "Props",
          "placeholder": "props",
          "section_id": "scene-props"
        },
        {
          "heading": "Continuity Notes",
          "placeholder": "continuity_notes",
          "section_id": "scene-continuity-notes"
        }
      ],
      "shot_type": "REFERENCE_SHEET",
      "visual_style_id": "sdc.cinematic-storyboard.v1"
    }
  ]
}
```
<!-- SDC-VISUAL-PROMPT-AGENT-JSON:END -->
