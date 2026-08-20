"""Pure, zero-authority real-asset use-plan consumer v2.6.

The consumer verifies the complete Pack-level Rights Manifest v2 closure and maps the
fourteen frozen assets into a deterministic ten-shot offline design.  A successful plan is
only eligible for a separate use-scope review.  It grants no Provider, generation, runtime,
posting, cost, or publication authority and performs no file, network, or clock I/O.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from sdc.compiler import compile_creative_sample, stable_id
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    CreativeSampleCompilation,
    CreativeSampleSpec,
    SceneAssetVersion,
    SceneBible,
)
from sdc.creative_pilot import (
    CreativeSamplePilotPack,
    build_creative_sample_pilot_documents,
)
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    CreativeSampleRealAssetIntakeTemplate,
    FrozenRealAssetDescriptor,
    RealAssetRequirement,
    build_real_asset_intake_template,
)
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
)
from sdc.real_asset_rights_manifest_v24 import (
    CreativeSampleRealAssetRightsManifestV2,
    RealAssetRightsManifestV24Error,
    verify_real_asset_rights_manifest_closure_v2,
)

USE_PLAN_V1_PROFILE: Literal[
    "creative-sample-real-asset-use-plan-consumer-v2.6"
] = "creative-sample-real-asset-use-plan-consumer-v2.6"
USE_PLAN_V1_POLICY_ID: Literal[
    "creative-sample-real-asset-use-plan-policy"
] = "creative-sample-real-asset-use-plan-policy"
USE_PLAN_V1_POLICY_VERSION: Literal["2.6.0"] = "2.6.0"
USE_PLAN_V1_POLICY_DOCUMENT_SHA256: Literal[
    "68ce2b32bfac11e88a19b3155d3935f47dc7334d79e97496245f046836b28775"
] = "68ce2b32bfac11e88a19b3155d3935f47dc7334d79e97496245f046836b28775"

PILOT_PACK_ID: Literal["creative_pilot_pack_b1041dbe27fc145c73c8"] = (
    "creative_pilot_pack_b1041dbe27fc145c73c8"
)
PILOT_SPEC_PAYLOAD_SHA256: Literal[
    "221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4"
] = "221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4"
PILOT_SPEC_DOCUMENT_SHA256: Literal[
    "43f7cb9949796a2d212e8b85aa23dc4e46eef22f1a2fcf10ad978d994ace261b"
] = "43f7cb9949796a2d212e8b85aa23dc4e46eef22f1a2fcf10ad978d994ace261b"
PILOT_COMPILATION_ID: Literal["creative_sample_c43253e73fe962f1623d"] = (
    "creative_sample_c43253e73fe962f1623d"
)
PILOT_COMPILATION_DOCUMENT_SHA256: Literal[
    "cd5a441fc1610435663ae3add96a14af9c2afe3c089202711ae9189181b3c8d5"
] = (
    "cd5a441fc1610435663ae3add96a14af9c2afe3c089202711ae9189181b3c8d5"
)
PILOT_ORDERED_SHOT_IDS = (
    "storyboard_shot_v2_6efad69a2a84e32dbc5b",
    "storyboard_shot_v2_13822570b72c80607da5",
    "storyboard_shot_v2_c506a9c24a958ea1645b",
    "storyboard_shot_v2_70097fbd380d13f419f7",
    "storyboard_shot_v2_c13ef471e7c016ef416f",
    "storyboard_shot_v2_c2f12fbc85044ad16dfb",
    "storyboard_shot_v2_99634ba94f4c01b7de21",
    "storyboard_shot_v2_8fe54fb039ee2c31e475",
    "storyboard_shot_v2_433f35b18c478ab1428c",
    "storyboard_shot_v2_64efc36a850a3781c7bb",
)
INTAKE_TEMPLATE_ID: Literal["real_asset_intake_template_58cfac98339ce9e36dce"] = (
    "real_asset_intake_template_58cfac98339ce9e36dce"
)
INTAKE_TEMPLATE_DOCUMENT_SHA256: Literal[
    "0c969aba4e885b8dc1fadd36d934c19dbc37cc5c0241651605ebdc6c7cdfccc8"
] = (
    "0c969aba4e885b8dc1fadd36d934c19dbc37cc5c0241651605ebdc6c7cdfccc8"
)
PROVIDER_NEUTRAL_BASELINE_SHA256: Literal[
    "b888bdb0dfd76444905b0287d6b424525463e2618e3f17d5fc49b3538f1aff11"
] = (
    "b888bdb0dfd76444905b0287d6b424525463e2618e3f17d5fc49b3538f1aff11"
)

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_PORTABLE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_JSON_LIMIT = 4_194_304
_POLICY_DOMAIN = b"sdc:creative-sample-real-asset-use-plan-policy:v2.6\0"
_BASELINE_DOMAIN = b"sdc:creative-sample-real-asset-provider-neutral-baseline:v1\0"


def _canonical_payload(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


_USE_PLAN_POLICY_PAYLOAD: dict[str, object] = {
    "consumer_scope": "OFFLINE_DESIGN_REVIEW_ONLY",
    "policy_id": USE_PLAN_V1_POLICY_ID,
    "policy_version": USE_PLAN_V1_POLICY_VERSION,
    "positive_manifest_status": "RIGHTS_MANIFEST_CREATED",
    "rules": (
        "EXACT_VERIFIED_RIGHTS_MANIFEST_CLOSURE",
        "EXACT_PROVIDER_NEUTRAL_PILOT_BASELINE",
        "EXACT_FOURTEEN_MEDIA_MAPPINGS",
        "DETERMINISTIC_NEW_SPEC_AND_COMPILATION",
        "PROPOSAL_CEILINGS_ARE_NOT_AUTHORITY",
        "NO_V1_RIGHTS_OR_REVISION_CONVERSION",
        "NO_GENERATION_NO_EXECUTION_NO_PROVIDER_AUTHORIZATION_NO_PUBLICATION",
    ),
}
if _sha256(_POLICY_DOMAIN + _canonical_payload(_USE_PLAN_POLICY_PAYLOAD)) != (
    USE_PLAN_V1_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("Use Plan v1 policy payload digest drifted")

_BASELINE_PAYLOAD: dict[str, object] = {
    "intake_template_document_sha256": INTAKE_TEMPLATE_DOCUMENT_SHA256,
    "intake_template_id": INTAKE_TEMPLATE_ID,
    "pilot_compilation_document_sha256": PILOT_COMPILATION_DOCUMENT_SHA256,
    "pilot_compilation_id": PILOT_COMPILATION_ID,
    "pilot_ordered_shot_ids": PILOT_ORDERED_SHOT_IDS,
    "pilot_pack_id": PILOT_PACK_ID,
    "pilot_spec_document_sha256": PILOT_SPEC_DOCUMENT_SHA256,
    "pilot_spec_payload_sha256": PILOT_SPEC_PAYLOAD_SHA256,
}
if _sha256(_BASELINE_DOMAIN + _canonical_payload(_BASELINE_PAYLOAD)) != (
    PROVIDER_NEUTRAL_BASELINE_SHA256
):
    raise RuntimeError("provider-neutral Pilot baseline digest drifted")


class RealAssetUsePlanV26Error(RuntimeError):
    """The pure real-asset Use Plan v2.6 consumer failed closed."""


class _UsePlanModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class ManifestClosureBindingV26(_UsePlanModel):
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_id: str = Field(pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$")
    evidence_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_territory: str = Field(min_length=1, max_length=256)
    evidence_use_scope: str = Field(min_length=1, max_length=1000)
    evidence_valid_until: str
    review_a_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_a_sha256: str = Field(pattern=_LOWER_SHA256)
    review_b_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_b_sha256: str = Field(pattern=_LOWER_SHA256)
    pair_check_id: str = Field(pattern=r"^real_asset_review_pair_check_v2_[0-9a-f]{20}$")
    pair_check_sha256: str = Field(pattern=_LOWER_SHA256)
    qualification_request_id: str = Field(
        pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$"
    )
    qualification_request_sha256: str = Field(pattern=_LOWER_SHA256)
    qualification_instruction_id: str = Field(
        pattern=r"^real_asset_qualification_decision_instruction_v22_[0-9a-f]{20}$"
    )
    qualification_instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    qualification_decision_id: str = Field(
        pattern=r"^real_asset_qualification_decision_v2_[0-9a-f]{20}$"
    )
    qualification_decision_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_id: str = Field(
        pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$"
    )
    rights_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_manifest_at: str


class ProviderNeutralBaselineProjectionV26(_UsePlanModel):
    pilot_pack_id: Literal["creative_pilot_pack_b1041dbe27fc145c73c8"]
    pilot_spec_payload_sha256: Literal[
        "221ccd64abeaa786f9271e89e70c2c8ab37e8f03790daa766f9b763aa25e0af4"
    ]
    pilot_spec_document_sha256: Literal[
        "43f7cb9949796a2d212e8b85aa23dc4e46eef22f1a2fcf10ad978d994ace261b"
    ]
    pilot_compilation_id: Literal["creative_sample_c43253e73fe962f1623d"]
    pilot_compilation_document_sha256: Literal[
        "cd5a441fc1610435663ae3add96a14af9c2afe3c089202711ae9189181b3c8d5"
    ]
    pilot_ordered_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    intake_template_id: Literal["real_asset_intake_template_58cfac98339ce9e36dce"]
    intake_template_document_sha256: Literal[
        "0c969aba4e885b8dc1fadd36d934c19dbc37cc5c0241651605ebdc6c7cdfccc8"
    ]
    projection_sha256: Literal[
        "b888bdb0dfd76444905b0287d6b424525463e2618e3f17d5fc49b3538f1aff11"
    ]

    @model_validator(mode="after")
    def validate_projection(self) -> ProviderNeutralBaselineProjectionV26:
        if self.pilot_ordered_shot_ids != PILOT_ORDERED_SHOT_IDS:
            raise ValueError("provider-neutral baseline must bind the exact ten Pilot shots")
        payload = self.model_dump(mode="json", exclude={"projection_sha256"})
        if _sha256(_BASELINE_DOMAIN + _canonical_payload(payload)) != self.projection_sha256:
            raise ValueError("provider-neutral baseline projection digest drifted")
        return self


UseRoleV26 = Literal[
    "CHARACTER_REFERENCE",
    "SCENE_REFERENCE",
    "DIALOGUE_AUDIO",
    "BACKGROUND_MUSIC",
]


class MediaMappingV26(_UsePlanModel):
    mapping_id: str = Field(pattern=r"^real_asset_use_mapping_v1_[0-9a-f]{20}$")
    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    kind: Literal["IMAGE", "VOICE", "BGM"]
    subject_kind: Literal["CHARACTER", "SCENE", "DIALOGUE", "SCORE"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    object_path: str
    media_type: Literal["image/png", "audio/wav"]
    media_sha256: str = Field(pattern=_LOWER_SHA256)
    media_size_bytes: Annotated[int, Field(gt=0)]
    duration_ms: Annotated[int, Field(ge=0)]
    source_authority: Literal[
        "USER_PROVIDED_LOCAL", "SEPARATELY_APPROVED_LOCAL_GENERATION"
    ]
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    technical_profile: str = Field(pattern=_PORTABLE_ID)
    technical_record_sha256: str = Field(pattern=_LOWER_SHA256)
    use_role: UseRoleV26
    target_id: str = Field(pattern=_PORTABLE_ID)
    timeline_start_ms: int | None = Field(default=None, ge=0)
    timeline_end_ms: int | None = Field(default=None, gt=0)
    exact_text: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_mapping(self) -> MediaMappingV26:
        if self.kind == "IMAGE":
            expected_role = (
                "CHARACTER_REFERENCE" if self.subject_kind == "CHARACTER" else "SCENE_REFERENCE"
            )
            if (
                self.subject_kind not in {"CHARACTER", "SCENE"}
                or self.use_role != expected_role
                or self.media_type != "image/png"
                or self.duration_ms != 0
                or self.timeline_start_ms is not None
                or self.timeline_end_ms is not None
                or self.exact_text is not None
            ):
                raise ValueError("image mapping must target one exact character or scene reference")
        elif self.kind == "VOICE":
            if (
                self.subject_kind != "DIALOGUE"
                or self.use_role != "DIALOGUE_AUDIO"
                or self.media_type != "audio/wav"
                or self.target_id != self.subject_id
                or self.timeline_start_ms is None
                or self.timeline_end_ms is None
                or self.timeline_start_ms >= self.timeline_end_ms
                or self.exact_text is None
            ):
                raise ValueError("voice mapping must bind one exact dialogue line and interval")
        elif (
            self.subject_kind != "SCORE"
            or self.use_role != "BACKGROUND_MUSIC"
            or self.media_type != "audio/wav"
            or self.timeline_start_ms != 0
            or self.timeline_end_ms != 72_000
            or self.duration_ms != 72_000
            or self.exact_text is not None
        ):
            raise ValueError("BGM mapping must bind the exact 72-second master clock")
        expected = stable_id(
            "real_asset_use_mapping_v1",
            self.model_dump(mode="json", exclude={"mapping_id"}),
        )
        if self.mapping_id != expected:
            raise ValueError("media mapping ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetUsePlanV1(_UsePlanModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-use-plan-v1"
    ] = "sdc.creative-sample-real-asset-use-plan-v1"
    profile: Literal[
        "creative-sample-real-asset-use-plan-consumer-v2.6"
    ] = USE_PLAN_V1_PROFILE
    plan_id: str = Field(pattern=r"^real_asset_use_plan_v1_[0-9a-f]{20}$")
    plan_policy_id: Literal[
        "creative-sample-real-asset-use-plan-policy"
    ] = USE_PLAN_V1_POLICY_ID
    plan_policy_version: Literal["2.6.0"] = USE_PLAN_V1_POLICY_VERSION
    plan_policy_document_sha256: Literal[
        "68ce2b32bfac11e88a19b3155d3935f47dc7334d79e97496245f046836b28775"
    ] = USE_PLAN_V1_POLICY_DOCUMENT_SHA256
    manifest_closure: ManifestClosureBindingV26
    source_mode: Literal["IMPORTED_MEDIA"] = "IMPORTED_MEDIA"
    consumer_scope: Literal["OFFLINE_DESIGN_REVIEW_ONLY"] = "OFFLINE_DESIGN_REVIEW_ONLY"
    baseline: ProviderNeutralBaselineProjectionV26
    planned_spec_payload_sha256: str = Field(pattern=_LOWER_SHA256)
    planned_spec_document_sha256: str = Field(pattern=_LOWER_SHA256)
    planned_compilation_id: str = Field(pattern=r"^creative_sample_[0-9a-f]{20}$")
    planned_compilation_document_sha256: str = Field(pattern=_LOWER_SHA256)
    planned_spec: CreativeSampleSpec
    planned_compilation: CreativeSampleCompilation
    planned_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    media_mappings: tuple[MediaMappingV26, ...] = Field(min_length=14, max_length=14)
    shot_count: Literal[10] = 10
    proposed_attempts_per_shot: Literal[2] = 2
    proposed_provider_requests_max: Literal[20] = 20
    proposed_image_generation_requests: Literal[0] = 0
    proposed_audio_generation_requests: Literal[0] = 0
    proposed_cost_ceiling_cny: Literal[450] = 450
    authorized_attempts: Literal[0] = 0
    authorized_cost_cny: Literal[0] = 0
    status: Literal["USE_PLAN_CANDIDATE_CREATED"] = "USE_PLAN_CANDIDATE_CREATED"
    rights_qualification_performed: Literal[True] = True
    rights_manifest_created: Literal[True] = True
    use_scope_review_performed: Literal[False] = False
    eligible_for_separate_use_scope_review: Literal[True] = True
    eligible_for_separate_provider_proposal: Literal[False] = False
    eligible_for_separate_provider_approval: Literal[False] = False
    provider_approval_granted: Literal[False] = False
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_real_generation: Literal[False] = False
    generation_authorized: Literal[False] = False
    execution_authorized: Literal[False] = False
    publication_authorized: Literal[False] = False
    remote_processing_allowed: Literal[False] = False
    retention_allowed: Literal[False] = False
    training_allowed: Literal[False] = False
    publication_allowed: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="before")
    @classmethod
    def validate_exact_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        boolean_fields = (
            "rights_qualification_performed",
            "rights_manifest_created",
            "use_scope_review_performed",
            "eligible_for_separate_use_scope_review",
            "eligible_for_separate_provider_proposal",
            "eligible_for_separate_provider_approval",
            "provider_approval_granted",
            "eligible_for_real_generation",
            "generation_authorized",
            "execution_authorized",
            "publication_authorized",
            "remote_processing_allowed",
            "retention_allowed",
            "training_allowed",
            "publication_allowed",
        )
        for field in boolean_fields:
            if field in value and type(value[field]) is not bool:
                raise ValueError(f"{field} must be an exact JSON boolean")
        integer_fields = (
            "shot_count",
            "proposed_attempts_per_shot",
            "proposed_provider_requests_max",
            "proposed_image_generation_requests",
            "proposed_audio_generation_requests",
            "proposed_cost_ceiling_cny",
            "authorized_attempts",
            "authorized_cost_cny",
            "posts_allowed",
            "provider_requests",
        )
        for field in integer_fields:
            if field in value and type(value[field]) is not int:
                raise ValueError(f"{field} must be an exact JSON integer")
        return value

    @model_validator(mode="after")
    def validate_plan(self) -> CreativeSampleRealAssetUsePlanV1:
        if self.baseline.pilot_ordered_shot_ids != PILOT_ORDERED_SHOT_IDS:
            raise ValueError("Use Plan predecessor shots drifted from the pinned Pilot")
        if self.planned_spec_payload_sha256 != _sha256(_canonical_payload(self.planned_spec)):
            raise ValueError("Use Plan must bind the exact planned specification payload")
        if self.planned_spec_document_sha256 != _sha256(_canonical_document(self.planned_spec)):
            raise ValueError("Use Plan must bind the exact planned specification document")
        rebuilt = compile_creative_sample(self.planned_spec)
        if self.planned_compilation != rebuilt:
            raise ValueError("Use Plan compilation must be an exact pure rebuild")
        if self.planned_compilation_id != rebuilt.id:
            raise ValueError("Use Plan compilation ID drifted")
        if self.planned_compilation_document_sha256 != _sha256(_canonical_document(rebuilt)):
            raise ValueError("Use Plan must bind the exact planned compilation document")
        expected_shots = tuple(item.id for item in rebuilt.pir.shots)
        if self.planned_shot_ids != expected_shots or len(set(expected_shots)) != 10:
            raise ValueError("Use Plan must bind exactly ten unique compiled shots")
        if any(
            current == predecessor
            for current, predecessor in zip(
                self.planned_shot_ids,
                self.baseline.pilot_ordered_shot_ids,
                strict=True,
            )
        ):
            raise ValueError("every planned real-media shot must differ from the Pilot fixture")
        if tuple(item.ordinal for item in self.media_mappings) != tuple(range(14)):
            raise ValueError("Use Plan media mappings must preserve all fourteen ordinals")
        if tuple(item.kind for item in self.media_mappings) != (
            "IMAGE",
            "IMAGE",
            "IMAGE",
            "IMAGE",
            *("VOICE" for _ in range(9)),
            "BGM",
        ):
            raise ValueError("Use Plan must contain four images, nine voices, and one BGM")
        if len({item.mapping_id for item in self.media_mappings}) != 14:
            raise ValueError("Use Plan media mapping IDs must be unique")
        if len({item.requirement_id for item in self.media_mappings}) != 14:
            raise ValueError("Use Plan media requirements must be unique")
        if len({item.media_sha256 for item in self.media_mappings}) != 14:
            raise ValueError("Use Plan media byte identities must be unique")
        active_versions = {
            bible.character_id: bible.active_asset_version_id
            for bible in self.planned_spec.character_bibles
        } | {
            bible.scene_id: bible.active_asset_version_id
            for bible in self.planned_spec.scene_bibles
        }
        dialogue = {item.line_id: item for item in self.planned_spec.dialogue}
        for mapping in self.media_mappings:
            if (
                mapping.kind == "IMAGE"
                and active_versions.get(mapping.subject_id) != mapping.target_id
            ):
                raise ValueError("image mapping must target the exact active planned asset version")
            if mapping.kind == "VOICE":
                line = dialogue.get(mapping.target_id)
                if line is None or (
                    mapping.timeline_start_ms,
                    mapping.timeline_end_ms,
                    mapping.exact_text,
                ) != (line.start_ms, line.end_ms, line.text):
                    raise ValueError("voice mapping must match the exact planned dialogue")
            if mapping.kind == "BGM" and mapping.target_id != rebuilt.audio_clock.id:
                raise ValueError("BGM mapping must target the exact planned audio clock")
        if self.proposed_provider_requests_max != (
            self.shot_count * self.proposed_attempts_per_shot
        ):
            raise ValueError("planning request ceiling must equal ten shots times two attempts")
        expected_id = stable_id(
            "real_asset_use_plan_v1",
            self.model_dump(mode="json", exclude={"plan_id"}),
        )
        if self.plan_id != expected_id:
            raise ValueError("Use Plan ID must bind its complete canonical content")
        return self


def _revalidate[ModelT: BaseModel](value: ModelT, model: type[ModelT], *, field: str) -> ModelT:
    try:
        before = _canonical_document(value)
        rebuilt = model.model_validate(value.model_dump(mode="python"), strict=True)
        after = _canonical_document(rebuilt)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RealAssetUsePlanV26Error(f"{field} violates its strict contract") from exc
    if before != after:
        raise RealAssetUsePlanV26Error(f"{field} changes canonical bytes during revalidation")
    return rebuilt


def _assert_pinned_baseline() -> tuple[
    CreativeSampleSpec,
    CreativeSamplePilotPack,
    CreativeSampleRealAssetIntakeTemplate,
]:
    pilot_spec, pilot_pack = build_creative_sample_pilot_documents()
    pilot_compilation = compile_creative_sample(pilot_spec)
    template = build_real_asset_intake_template()
    observed = (
        pilot_pack.pack_id,
        _sha256(_canonical_payload(pilot_spec)),
        _sha256(_canonical_document(pilot_spec)),
        pilot_compilation.id,
        _sha256(_canonical_document(pilot_compilation)),
        pilot_pack.ordered_shot_ids,
        template.template_id,
        _sha256(_canonical_document(template)),
    )
    expected = (
        PILOT_PACK_ID,
        PILOT_SPEC_PAYLOAD_SHA256,
        PILOT_SPEC_DOCUMENT_SHA256,
        PILOT_COMPILATION_ID,
        PILOT_COMPILATION_DOCUMENT_SHA256,
        PILOT_ORDERED_SHOT_IDS,
        INTAKE_TEMPLATE_ID,
        INTAKE_TEMPLATE_DOCUMENT_SHA256,
    )
    if observed != expected:
        raise RealAssetUsePlanV26Error("the pinned provider-neutral Pilot baseline drifted")
    return pilot_spec, pilot_pack, template


def _planning_binding_ref(
    *,
    manifest: CreativeSampleRealAssetRightsManifestV2,
    manifest_sha256: str,
    descriptor: FrozenRealAssetDescriptor,
    subject_kind: str,
) -> str:
    return stable_id(
        "real_asset_use_plan_binding_v1",
        {
            "media_sha256": descriptor.sha256,
            "requirement_id": descriptor.requirement_id,
            "rights_manifest_id": manifest.manifest_id,
            "rights_manifest_sha256": manifest_sha256,
            "subject_id": descriptor.subject_id,
            "subject_kind": subject_kind,
            "technical_record_sha256": descriptor.technical_record_sha256,
        },
    )


def _derive_planned_spec(
    *,
    pilot_spec: CreativeSampleSpec,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    requirements: tuple[RealAssetRequirement, ...],
    manifest: CreativeSampleRealAssetRightsManifestV2,
    manifest_sha256: str,
) -> CreativeSampleSpec:
    descriptor_by_subject = {item.subject_id: item for item in pack.objects if item.kind == "IMAGE"}
    requirement_by_subject = {
        item.subject_id: item for item in requirements if item.kind == "IMAGE"
    }
    characters: list[CharacterBible] = []
    for source in pilot_spec.character_bibles:
        descriptor = descriptor_by_subject.get(source.character_id)
        requirement = requirement_by_subject.get(source.character_id)
        if descriptor is None or requirement is None or requirement.subject_kind != "CHARACTER":
            raise RealAssetUsePlanV26Error("Pack lacks one exact character reference")
        reference = _planning_binding_ref(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            descriptor=descriptor,
            subject_kind="CHARACTER",
        )
        version_id = CharacterAssetVersion.derive_id(
            character_id=source.character_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=reference,
            visual_description=source.visual_description,
        )
        version = CharacterAssetVersion(
            id=version_id,
            character_id=source.character_id,
            version=2,
            content_sha256=descriptor.sha256,
            approval_ref=reference,
            visual_description=source.visual_description,
        )
        characters.append(
            CharacterBible(
                character_id=source.character_id,
                name=source.name,
                visual_description=source.visual_description,
                asset_versions=(version,),
                active_asset_version_id=version.id,
            )
        )
    scenes: list[SceneBible] = []
    for scene_source in pilot_spec.scene_bibles:
        descriptor = descriptor_by_subject.get(scene_source.scene_id)
        requirement = requirement_by_subject.get(scene_source.scene_id)
        if descriptor is None or requirement is None or requirement.subject_kind != "SCENE":
            raise RealAssetUsePlanV26Error("Pack lacks one exact scene reference")
        reference = _planning_binding_ref(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            descriptor=descriptor,
            subject_kind="SCENE",
        )
        version_id = SceneAssetVersion.derive_id(
            scene_id=scene_source.scene_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=reference,
            visual_description=scene_source.visual_description,
        )
        scene_version = SceneAssetVersion(
            id=version_id,
            scene_id=scene_source.scene_id,
            version=2,
            content_sha256=descriptor.sha256,
            approval_ref=reference,
            visual_description=scene_source.visual_description,
        )
        scenes.append(
            SceneBible(
                scene_id=scene_source.scene_id,
                ordinal=scene_source.ordinal,
                name=scene_source.name,
                visual_description=scene_source.visual_description,
                asset_versions=(scene_version,),
                active_asset_version_id=scene_version.id,
            )
        )
    return CreativeSampleSpec(
        title=pilot_spec.title,
        seed=pilot_spec.seed,
        duration_ms=pilot_spec.duration_ms,
        character_bibles=tuple(characters),
        scene_bibles=tuple(scenes),
        dialogue=pilot_spec.dialogue,
        shots=pilot_spec.shots,
    )


def _mapping(
    *,
    descriptor: FrozenRealAssetDescriptor,
    requirement: RealAssetRequirement,
    spec: CreativeSampleSpec,
    compilation: CreativeSampleCompilation,
) -> MediaMappingV26:
    if (
        descriptor.ordinal != requirement.ordinal
        or descriptor.requirement_id != requirement.requirement_id
        or descriptor.kind != requirement.kind
        or descriptor.subject_id != requirement.subject_id
        or descriptor.logical_path != requirement.logical_path
        or descriptor.media_type != requirement.media_type
        or descriptor.technical_profile != requirement.technical_profile
    ):
        raise RealAssetUsePlanV26Error("Pack object drifted from its exact intake requirement")
    if descriptor.kind == "IMAGE":
        active = {
            bible.character_id: bible.active_asset_version_id for bible in spec.character_bibles
        } | {bible.scene_id: bible.active_asset_version_id for bible in spec.scene_bibles}
        use_role: UseRoleV26 = (
            "CHARACTER_REFERENCE"
            if requirement.subject_kind == "CHARACTER"
            else "SCENE_REFERENCE"
        )
        target_id = active[requirement.subject_id]
        start = end = None
        text = None
    elif descriptor.kind == "VOICE":
        use_role = "DIALOGUE_AUDIO"
        target_id = requirement.subject_id
        start = requirement.start_ms
        end = requirement.end_ms
        text = requirement.exact_text
    else:
        use_role = "BACKGROUND_MUSIC"
        target_id = compilation.audio_clock.id
        start = requirement.start_ms
        end = requirement.end_ms
        text = None
    payload: dict[str, object] = {
        "ordinal": descriptor.ordinal,
        "requirement_id": descriptor.requirement_id,
        "kind": descriptor.kind,
        "subject_kind": requirement.subject_kind,
        "subject_id": descriptor.subject_id,
        "logical_path": descriptor.logical_path,
        "object_path": descriptor.object_path,
        "media_type": descriptor.media_type,
        "media_sha256": descriptor.sha256,
        "media_size_bytes": descriptor.size_bytes,
        "duration_ms": descriptor.duration_ms,
        "source_authority": descriptor.source_authority,
        "provenance_record_sha256": descriptor.provenance_record_sha256,
        "technical_profile": descriptor.technical_profile,
        "technical_record_sha256": descriptor.technical_record_sha256,
        "use_role": use_role,
        "target_id": target_id,
        "timeline_start_ms": start,
        "timeline_end_ms": end,
        "exact_text": text,
    }
    return MediaMappingV26.model_validate(
        {"mapping_id": stable_id("real_asset_use_mapping_v1", payload), **payload},
        strict=True,
    )


def build_real_asset_use_plan_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    qualification_request: CreativeSampleRealAssetQualificationRequestV2,
    qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    qualification_decision: CreativeSampleRealAssetQualificationDecisionV2,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
) -> CreativeSampleRealAssetUsePlanV1:
    """Compile one deterministic, provider-neutral, zero-authority Use Plan."""

    pack = _revalidate(pack, CreativeSampleFrozenRealAssetPackManifest, field="frozen Pack")
    evidence = _revalidate(
        evidence,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        field="rights Evidence",
    )
    reviewer_a = _revalidate(
        reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer A record",
    )
    reviewer_b = _revalidate(
        reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer B record",
    )
    pair_check = _revalidate(
        pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        field="review PairCheck",
    )
    qualification_request = _revalidate(
        qualification_request,
        CreativeSampleRealAssetQualificationRequestV2,
        field="qualification Request",
    )
    qualification_instruction = _revalidate(
        qualification_instruction,
        CreativeSampleRealAssetQualificationDecisionInstructionV22,
        field="qualification Instruction",
    )
    qualification_decision = _revalidate(
        qualification_decision,
        CreativeSampleRealAssetQualificationDecisionV2,
        field="qualification Decision",
    )
    rights_manifest = _revalidate(
        rights_manifest,
        CreativeSampleRealAssetRightsManifestV2,
        field="Rights Manifest",
    )
    try:
        rights_manifest = verify_real_asset_rights_manifest_closure_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            pair_check=pair_check,
            request=qualification_request,
            instruction=qualification_instruction,
            decision=qualification_decision,
            manifest=rights_manifest,
        )
    except (RealAssetRightsManifestV24Error, ValidationError, ValueError) as exc:
        raise RealAssetUsePlanV26Error(
            "Use Plan requires the exact verified Rights Manifest closure"
        ) from exc
    pilot_spec, pilot_pack, template_obj = _assert_pinned_baseline()
    template = template_obj
    if not hasattr(template, "requirements"):
        raise RealAssetUsePlanV26Error("pinned intake template has an invalid contract")
    if pack.template_id != INTAKE_TEMPLATE_ID or pack.pilot_pack_id != PILOT_PACK_ID:
        raise RealAssetUsePlanV26Error("Pack does not bind the pinned provider-neutral baseline")
    manifest_sha = _sha256(_canonical_document(rights_manifest))
    planned_spec = _derive_planned_spec(
        pilot_spec=pilot_spec,
        pack=pack,
        requirements=template.requirements,
        manifest=rights_manifest,
        manifest_sha256=manifest_sha,
    )
    planned_compilation = compile_creative_sample(planned_spec)
    if planned_compilation.id == pilot_pack.compilation_id:
        raise RealAssetUsePlanV26Error("planned compilation inherited the Pilot identity")
    mappings = tuple(
        _mapping(
            descriptor=descriptor,
            requirement=requirement,
            spec=planned_spec,
            compilation=planned_compilation,
        )
        for descriptor, requirement in zip(pack.objects, template.requirements, strict=True)
    )
    closure = ManifestClosureBindingV26(
        pack_id=pack.pack_id,
        pack_manifest_sha256=_sha256(_canonical_document(pack)),
        evidence_id=evidence.bundle_id,
        evidence_sha256=_sha256(_canonical_document(evidence)),
        evidence_territory=evidence.territory,
        evidence_use_scope=evidence.use_scope,
        evidence_valid_until=evidence.valid_until,
        review_a_id=reviewer_a.review_id,
        review_a_sha256=_sha256(_canonical_document(reviewer_a)),
        review_b_id=reviewer_b.review_id,
        review_b_sha256=_sha256(_canonical_document(reviewer_b)),
        pair_check_id=pair_check.pair_check_id,
        pair_check_sha256=_sha256(_canonical_document(pair_check)),
        qualification_request_id=qualification_request.request_id,
        qualification_request_sha256=_sha256(_canonical_document(qualification_request)),
        qualification_instruction_id=qualification_instruction.instruction_id,
        qualification_instruction_sha256=_sha256(
            _canonical_document(qualification_instruction)
        ),
        qualification_decision_id=qualification_decision.decision_id,
        qualification_decision_sha256=_sha256(_canonical_document(qualification_decision)),
        rights_manifest_id=rights_manifest.manifest_id,
        rights_manifest_sha256=manifest_sha,
        rights_manifest_at=rights_manifest.manifest_at,
    )
    baseline = ProviderNeutralBaselineProjectionV26(
        pilot_pack_id=PILOT_PACK_ID,
        pilot_spec_payload_sha256=PILOT_SPEC_PAYLOAD_SHA256,
        pilot_spec_document_sha256=PILOT_SPEC_DOCUMENT_SHA256,
        pilot_compilation_id=PILOT_COMPILATION_ID,
        pilot_compilation_document_sha256=PILOT_COMPILATION_DOCUMENT_SHA256,
        pilot_ordered_shot_ids=PILOT_ORDERED_SHOT_IDS,
        intake_template_id=INTAKE_TEMPLATE_ID,
        intake_template_document_sha256=INTAKE_TEMPLATE_DOCUMENT_SHA256,
        projection_sha256=PROVIDER_NEUTRAL_BASELINE_SHA256,
    )
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-plan-v1",
        "profile": USE_PLAN_V1_PROFILE,
        "plan_policy_id": USE_PLAN_V1_POLICY_ID,
        "plan_policy_version": USE_PLAN_V1_POLICY_VERSION,
        "plan_policy_document_sha256": USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        "manifest_closure": closure.model_dump(mode="json"),
        "source_mode": "IMPORTED_MEDIA",
        "consumer_scope": "OFFLINE_DESIGN_REVIEW_ONLY",
        "baseline": baseline.model_dump(mode="json"),
        "planned_spec_payload_sha256": _sha256(_canonical_payload(planned_spec)),
        "planned_spec_document_sha256": _sha256(_canonical_document(planned_spec)),
        "planned_compilation_id": planned_compilation.id,
        "planned_compilation_document_sha256": _sha256(
            _canonical_document(planned_compilation)
        ),
        "planned_spec": planned_spec.model_dump(mode="json"),
        "planned_compilation": planned_compilation.model_dump(mode="json"),
        "planned_shot_ids": tuple(item.id for item in planned_compilation.pir.shots),
        "media_mappings": tuple(item.model_dump(mode="json") for item in mappings),
        "shot_count": 10,
        "proposed_attempts_per_shot": 2,
        "proposed_provider_requests_max": 20,
        "proposed_image_generation_requests": 0,
        "proposed_audio_generation_requests": 0,
        "proposed_cost_ceiling_cny": 450,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "status": "USE_PLAN_CANDIDATE_CREATED",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "use_scope_review_performed": False,
        "eligible_for_separate_use_scope_review": True,
        "eligible_for_separate_provider_proposal": False,
        "eligible_for_separate_provider_approval": False,
        "provider_approval_granted": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    try:
        strict_payload = {
            **payload,
            "manifest_closure": closure,
            "baseline": baseline,
            "planned_spec": planned_spec,
            "planned_compilation": planned_compilation,
            "media_mappings": mappings,
        }
        return CreativeSampleRealAssetUsePlanV1.model_validate(
            {
                "plan_id": stable_id("real_asset_use_plan_v1", payload),
                **strict_payload,
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUsePlanV26Error("Use Plan could not be built") from exc


def verify_real_asset_use_plan_closure_v1(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    qualification_request: CreativeSampleRealAssetQualificationRequestV2,
    qualification_instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    qualification_decision: CreativeSampleRealAssetQualificationDecisionV2,
    rights_manifest: CreativeSampleRealAssetRightsManifestV2,
    use_plan: CreativeSampleRealAssetUsePlanV1,
) -> CreativeSampleRealAssetUsePlanV1:
    """Historically rebuild an exact Use Plan without reading current time."""

    use_plan = _revalidate(
        use_plan,
        CreativeSampleRealAssetUsePlanV1,
        field="real-asset Use Plan",
    )
    rebuilt = build_real_asset_use_plan_v1(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        qualification_request=qualification_request,
        qualification_instruction=qualification_instruction,
        qualification_decision=qualification_decision,
        rights_manifest=rights_manifest,
    )
    if rebuilt != use_plan:
        raise RealAssetUsePlanV26Error("Use Plan drifted from its exact verified closure")
    return use_plan


def _reject_json_constant(value: str) -> None:
    raise RealAssetUsePlanV26Error(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetUsePlanV26Error(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def parse_real_asset_use_plan_v1_json(raw: bytes) -> CreativeSampleRealAssetUsePlanV1:
    """Parse one bounded, exact-canonical in-memory Use Plan document."""

    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > _JSON_LIMIT
        or raw.startswith(b"\xef\xbb\xbf")
    ):
        raise RealAssetUsePlanV26Error("Use Plan JSON must be bounded BOM-free bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise RealAssetUsePlanV26Error("Use Plan JSON is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RealAssetUsePlanV26Error("Use Plan JSON must contain one object")
    try:
        candidate = CreativeSampleRealAssetUsePlanV1.model_validate_json(raw, strict=False)
        plan = CreativeSampleRealAssetUsePlanV1.model_validate(
            candidate.model_dump(mode="python"),
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetUsePlanV26Error("Use Plan JSON violates its strict contract") from exc
    if raw != _canonical_document(plan):
        raise RealAssetUsePlanV26Error("Use Plan JSON is not the exact canonical document")
    return plan


__all__ = [
    "PROVIDER_NEUTRAL_BASELINE_SHA256",
    "USE_PLAN_V1_POLICY_DOCUMENT_SHA256",
    "USE_PLAN_V1_POLICY_ID",
    "USE_PLAN_V1_POLICY_VERSION",
    "USE_PLAN_V1_PROFILE",
    "CreativeSampleRealAssetUsePlanV1",
    "ManifestClosureBindingV26",
    "MediaMappingV26",
    "ProviderNeutralBaselineProjectionV26",
    "RealAssetUsePlanV26Error",
    "build_real_asset_use_plan_v1",
    "parse_real_asset_use_plan_v1_json",
    "verify_real_asset_use_plan_closure_v1",
]
