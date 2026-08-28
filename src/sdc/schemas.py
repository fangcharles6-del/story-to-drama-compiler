"""Generate and check committed contract JSON schemas."""

import json
from pathlib import Path

from pydantic import BaseModel

from sdc import contracts
from sdc.creative_pilot import CreativeSamplePilotPack, CreativeSamplePilotSpecDocument
from sdc.real_asset_intake import (
    CreativeSampleFrozenRealAssetPackManifest,
    CreativeSampleRealAssetGapReport,
    CreativeSampleRealAssetIntakeTemplate,
    CreativeSampleRealAssetRevision,
    CreativeSampleRealAssetRightsManifest,
    CreativeSampleRealAssetSpecDocument,
    CreativeSampleRealAssetSubmission,
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
from sdc.real_asset_rights_manifest_v24 import CreativeSampleRealAssetRightsManifestV2
from sdc.real_asset_use_plan_v26 import CreativeSampleRealAssetUsePlanV1
from sdc.real_asset_use_scope_review_v26 import (
    CreativeSampleRealAssetUseScopeReviewDecisionV1,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
)
from sdc.visual_prompt_compiler import (
    CreativeSampleVisualPromptCompileRequestV1,
    CreativeSampleVisualPromptSidecarV1,
)
from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptArtifactV1,
    CreativeSampleReferenceVisualPromptCompileRequestV1,
)

from .real_asset_fresh_status_evidence_v30 import (
    CreativeSampleRealAssetFreshStatusDecisionV1,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusInstructionV1,
    CreativeSampleRealAssetFreshStatusRequestV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
)
from .real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
    CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
)

MODELS: list[type[BaseModel]] = [
    contracts.StoryInput,
    contracts.NIR,
    contracts.PIR,
    contracts.AudioMasterClock,
    contracts.JobGraph,
    contracts.GenerationJob,
    contracts.AssemblyPlan,
    contracts.CharacterAssetVersion,
    contracts.CharacterBible,
    contracts.SceneAssetVersion,
    contracts.SceneBible,
    contracts.DialogueLine,
    contracts.CreativeSampleShotSpec,
    contracts.CreativeSampleSpec,
    contracts.NIRSceneV2,
    contracts.NIRV2,
    contracts.CharacterAssetBinding,
    contracts.StoryboardShotV2,
    contracts.PIRV2,
    contracts.CreativeSampleMetrics,
    contracts.CreativeSampleCompilation,
    contracts.RunEvent,
    contracts.QCReport,
    contracts.QCEvidence,
    contracts.ReleaseManifest,
    contracts.ProviderProfile,
    contracts.ProviderRequest,
    contracts.ProviderSubmission,
    contracts.ProviderTaskSnapshot,
    contracts.DownloadedArtifact,
    contracts.ProviderFailure,
    contracts.CancelResult,
    contracts.ProviderCapabilitySnapshot,
    contracts.ProviderPricingSnapshot,
    contracts.ArkCanaryEntitlementSnapshot,
    contracts.LiveAuthorization,
    contracts.CanaryPlan,
    contracts.EvidenceBoundCanaryPlan,
    contracts.EvidenceBoundLiveAuthorization,
    contracts.CanaryExecution,
    contracts.EvidenceBundle,
    CreativeSamplePilotSpecDocument,
    CreativeSamplePilotPack,
    CreativeSampleRealAssetIntakeTemplate,
    CreativeSampleRealAssetSubmission,
    CreativeSampleRealAssetGapReport,
    CreativeSampleFrozenRealAssetPackManifest,
    CreativeSampleRealAssetRightsManifest,
    CreativeSampleRealAssetSpecDocument,
    CreativeSampleRealAssetRevision,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetQualificationRequestV2,
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
    CreativeSampleRealAssetRightsManifestV2,
    CreativeSampleRealAssetUsePlanV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewDecisionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
    CreativeSampleRealAssetFreshStatusRequestV1,
    CreativeSampleRealAssetFreshStatusInstructionV1,
    CreativeSampleRealAssetFreshStatusDecisionV1,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    CreativeSampleVisualPromptCompileRequestV1,
    CreativeSampleVisualPromptSidecarV1,
    CreativeSampleReferenceVisualPromptCompileRequestV1,
    CreativeSampleReferenceVisualPromptArtifactV1,
]


def generate(root: Path = Path("schemas")) -> None:
    root.mkdir(exist_ok=True)
    expected = set()
    for model in MODELS:
        target = root / f"{model.__name__}.schema.json"
        target.write_text(json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n")
        expected.add(target.name)
    for old in root.glob("*.schema.json"):
        if old.name not in expected:
            old.unlink()


if __name__ == "__main__":
    generate()
