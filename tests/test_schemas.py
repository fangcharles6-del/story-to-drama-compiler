import hashlib
import json
from decimal import Decimal
from pathlib import Path

from sdc.contracts import (
    EvidenceBoundLiveAuthorization,
    ProviderFailure,
    ProviderPricingSnapshot,
)
from sdc.real_asset_fresh_status_evidence_v30 import (
    CreativeSampleRealAssetFreshStatusDecisionV1,
    CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    CreativeSampleRealAssetFreshStatusInstructionV1,
    CreativeSampleRealAssetFreshStatusRequestV1,
    CreativeSampleRealAssetFreshStatusSourceObservationV1,
)
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
)
from sdc.real_asset_rights_manifest_v24 import CreativeSampleRealAssetRightsManifestV2
from sdc.real_asset_use_plan_v26 import (
    USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUsePlanV1,
)
from sdc.real_asset_use_scope_review_v26 import (
    USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUseScopeReviewDecisionV1,
    CreativeSampleRealAssetUseScopeReviewInstructionV1,
    CreativeSampleRealAssetUseScopeReviewRecordV1,
    CreativeSampleRealAssetUseScopeReviewRequestV1,
)
from sdc.schemas import MODELS

PRE_V2_SCHEMA_SHA256 = {
    "ArkCanaryEntitlementSnapshot.schema.json": (
        "c289f22e5f4baacdc01777ede575350abd20debc5297d346147468a265396971"
    ),
    "AssemblyPlan.schema.json": (
        "6af89970dc63dd1805470f03b83f3b63ed340bc660390d3fcd4987ec379e1a5f"
    ),
    "AudioMasterClock.schema.json": (
        "322405fc6cd65c3de3ab2aa84af19753f046740924930516822c14309695bd66"
    ),
    "CanaryExecution.schema.json": (
        "9bc5d46a1771e96c28cdab82038dc93baa74d55acfa7a9b757b291e321b64a16"
    ),
    "CanaryPlan.schema.json": ("63cc1b14fdd34ecbf80a3693e097b29f9bc79d64015ab001f891cb29a90366bf"),
    "CancelResult.schema.json": (
        "1b1b0e698bb7c88433de74761b151a4f8d288512f9e3d1e3d00cf84c3122eeac"
    ),
    "CharacterAssetBinding.schema.json": (
        "78454eb3dc9b5bfe83261642581834e9b929c29a90568da11d62f24e3a9352b4"
    ),
    "CharacterAssetVersion.schema.json": (
        "d812dea70169f90676133e727f3d15379b2d5fdfe1fd7216f511abff5c7494ac"
    ),
    "CharacterBible.schema.json": (
        "3758c6ee47dd28c86800d6239dc996e83bb446327a9a2cd75fa1483a44f8722d"
    ),
    "CreativeSampleCompilation.schema.json": (
        "1cf20fc6d8da596b6d36eee146c96b228be23ba018d72f0b30945fc665181d03"
    ),
    "CreativeSampleFrozenRealAssetPackManifest.schema.json": (
        "827d3c0b39453e5b78b92b80263aeecd2cda402308b6341ed7d1470397804f88"
    ),
    "CreativeSampleMetrics.schema.json": (
        "8b595ce379064c9ca3b439a037150e3f4572a7e994011949b43b5e08321f64ff"
    ),
    "CreativeSamplePilotPack.schema.json": (
        "269ecf1bff4f3b25b89a0954c143ebbece9b1f60a08e2e91d20f2c6a2f938239"
    ),
    "CreativeSamplePilotSpecDocument.schema.json": (
        "09884ccc1a461e7075cc78604d5b9d94e0dfa3d741e54c138f963ba12afda388"
    ),
    "CreativeSampleRealAssetGapReport.schema.json": (
        "50ffbdf295fcbf3dacceeefb56827617f4d91a77aea5c2f912c5636327033e76"
    ),
    "CreativeSampleRealAssetIntakeTemplate.schema.json": (
        "f10a7dbcc8b4a51dc5d14038649062b80b3095bea3fbdc92011dda88ebef12db"
    ),
    "CreativeSampleRealAssetRevision.schema.json": (
        "cf31fa596eeb5e7e14d3a7b4eaab9ebfe13bfca8f514cad9c97c9046ea6649eb"
    ),
    "CreativeSampleRealAssetRightsManifest.schema.json": (
        "3a278d1fead1834d706dd7b65bcfe10d3cf65798eab9787895fd2a5c8275c170"
    ),
    "CreativeSampleRealAssetSpecDocument.schema.json": (
        "08ea03f35485fa009efdfcbaf5c023ac6c1774e50c146d2adedca3867ec326e6"
    ),
    "CreativeSampleRealAssetSubmission.schema.json": (
        "635a169e199dc5e2b1eaf50ffe69bd234a97d2876a969dbf0d40da499c440b70"
    ),
    "CreativeSampleShotSpec.schema.json": (
        "08faba27cb527a61f99683f3e30dda432d599ff0a03ea0e37110caee5d057db8"
    ),
    "CreativeSampleSpec.schema.json": (
        "2c52d82e796936caef93f74f524aeb9870edbd5dea5dd79b2ff91d030a120a3c"
    ),
    "DialogueLine.schema.json": (
        "9a8d560848afcdd6cd050dae3e103487c7ca465bba91fc40e357a1cd28eacfa1"
    ),
    "DownloadedArtifact.schema.json": (
        "014172ebda7e5cf4dfe3ab3823f42be160b513715665664292cdb8f7b79123bc"
    ),
    "EvidenceBoundCanaryPlan.schema.json": (
        "112f956896efd6856f5877ee84d38a3bfe825ec4509740bb81fb68103ba72ea0"
    ),
    "EvidenceBoundLiveAuthorization.schema.json": (
        "b143e058753d77e9d7ac2b3c15ccb6bb891e8e370bf04ec48bf8f02b4a894cee"
    ),
    "EvidenceBundle.schema.json": (
        "2e1567f3f1d4caf52be697cb71073be02a574f82c16a7998ba46b49b5d2df596"
    ),
    "GenerationJob.schema.json": (
        "376cfa1f0096ba77a98cfd23128be4b432ee9a362d34f8f66d589e07f0e62bab"
    ),
    "JobGraph.schema.json": ("17d312d080a7d5d849725cb0c96c1898e090281c2cbb8b826f00a0e3616c9132"),
    "LiveAuthorization.schema.json": (
        "d18d571c9ff374a1ce128de9b005d0aaff02d61de8b7f456c37f16089f0ec6ce"
    ),
    "NIR.schema.json": ("ddc2ca8ce2da365724a52c58d175f61ddd86285dcfa08618720e7decda08ad05"),
    "NIRSceneV2.schema.json": ("3c67d0a01e106c0a27fcda34d215a66916d9e21479dc60648df1130206b368bc"),
    "NIRV2.schema.json": ("6f818b5cddb72b37ea6e424099bc417542fcf638e10e8344346273ff77c2dfae"),
    "PIR.schema.json": ("48533b52f1886eee001282efe096591a216b5df8a6d914bfe31b830b8fb4dec4"),
    "PIRV2.schema.json": ("38a4c595bb66bd23d6363a638df4b743cbecbba053c54b3e47925fc759b0b034"),
    "ProviderCapabilitySnapshot.schema.json": (
        "2aef9e8142d2f04ec126711036b7369b82c28a1ad6841d6c27ca82171a71643f"
    ),
    "ProviderFailure.schema.json": (
        "6fc8a296a532baa3454de07df52c21ae5a8be342a23eeb48b4fbdbbe241c5bd8"
    ),
    "ProviderPricingSnapshot.schema.json": (
        "ffb9e32f172e71e7435e112f31593e439b5fb78d02f1071ec203d69c8344806f"
    ),
    "ProviderProfile.schema.json": (
        "0897390f4f04d00f3b47bea4050832909f3bdcb7f15760cf43f1b1515b6bc685"
    ),
    "ProviderRequest.schema.json": (
        "33bdc2c1ec4d94dc69bbb0a4231a49b1b37d2227231f03098a8fb17a73e1cafb"
    ),
    "ProviderSubmission.schema.json": (
        "76ecde085a2b1780bb4fd6c9a3efdd6a0b951504173b55dd0a9abf6b636a6f66"
    ),
    "ProviderTaskSnapshot.schema.json": (
        "ad1d836abd9c16e4888f4723f86991077f6f31ed4ed54e4ef5771587b7340cb1"
    ),
    "QCEvidence.schema.json": ("fef0d47246737c98a7d8d99ed5fc86fb822485b1cd318300aa4f7a1ccdb9b548"),
    "QCReport.schema.json": ("e05f308ea9d0cf82792fe2a910819df0ce01a7b394b9258e4d867b30f0c9f8b6"),
    "ReleaseManifest.schema.json": (
        "5232a09b390cdaed8019b18d58134eb56ece3a9ac01c4419a17c7b4ccc8b44a5"
    ),
    "RunEvent.schema.json": ("ebc5626785cee74705f49798de58cb34ce4f18690bba9f894b782c855b14bc76"),
    "SceneAssetVersion.schema.json": (
        "3118c9c20e6c89a854faf2c5b85ebc6e3a903b1a5473b22854ea9293d6282759"
    ),
    "SceneBible.schema.json": ("b3902530148acb261976d387a9547d13269c2fb7d793040f8f4712f44813831f"),
    "StoryboardShotV2.schema.json": (
        "1f4060808e92e021701daf0f41fb574c9838af471e18d99da04568ed38160b69"
    ),
    "StoryInput.schema.json": ("4042419ae5c3fe068fe3b53105cca8110eb67fb2274ab935dea02c2dffc8b6c5"),
}

PRE_QUALIFICATION_REVIEW_V2_SCHEMA_SHA256 = {
    "CreativeSampleRealAssetRightsEvidenceBundleV2.schema.json": (
        "2ae3735a8d02cc94aacc3eb293863c8b5ee1a8ac562a541f9c42c712d13dfe6a"
    ),
    "CreativeSampleRealAssetHumanPackReviewV2.schema.json": (
        "5cc0176b8944fea35b97974a0b3bcc46eba08921851707823803261fd3d9d465"
    ),
    "CreativeSampleRealAssetReviewPairCheckV2.schema.json": (
        "b182f6fed61fc3b6feea644a885dc60231797b5506d493c8acdfd4329107acbd"
    ),
}
PRE_QUALIFICATION_SCHEMA_SHA256 = {
    **PRE_V2_SCHEMA_SHA256,
    **PRE_QUALIFICATION_REVIEW_V2_SCHEMA_SHA256,
}
PRE_REQUEST_PREPARER_SCHEMA_SHA256 = {
    **PRE_QUALIFICATION_SCHEMA_SHA256,
    "CreativeSampleRealAssetQualificationRequestV2.schema.json": (
        "ecc74efabc4f4e6d50d2f3b23dae6c222920586a77f9a1be5506edd22a6e606b"
    ),
    "CreativeSampleRealAssetQualificationDecisionV2.schema.json": (
        "56ffb2aa14476dffa2e7cc19a29a9333cae9ebcdd022b4adf08e64860f6d12a9"
    ),
}
PRE_INSTRUCTION_PREPARER_SCHEMA_SHA256 = {
    **PRE_REQUEST_PREPARER_SCHEMA_SHA256,
    "CreativeSampleRealAssetQualificationDecisionInstructionV22.schema.json": (
        "a6823db740274fc0806f95f7c66cf2b2092dc3bdd575796e00bbe5e5a566c251"
    ),
}
PRE_MANIFEST_FINALIZER_SCHEMA_SHA256 = {
    **PRE_INSTRUCTION_PREPARER_SCHEMA_SHA256,
    "CreativeSampleRealAssetRightsManifestV2.schema.json": (
        "54eb14e54df22f4bb2b3c09ef2d2f1c9490c7843732faa9586c6738abb392f50"
    ),
}
PRE_FRESH_STATUS_V30_SCHEMA_SHA256 = {
    **PRE_MANIFEST_FINALIZER_SCHEMA_SHA256,
    "CreativeSampleRealAssetUsePlanV1.schema.json": (
        "61fb95fc2016d72dff843a96bafe5fdfb9a6be047f48e9a0dd597bc956bb6a91"
    ),
    "CreativeSampleRealAssetUseScopeReviewRequestV1.schema.json": (
        "0bf762a9615794d74f5831e6adce8fa88ec633ca4df54125e895c1d1cd9e11db"
    ),
    "CreativeSampleRealAssetUseScopeReviewInstructionV1.schema.json": (
        "6b9cac6ac7d886dd68e55530acf2a4e1f7b6121d187ea6324f4640373f3da2ae"
    ),
    "CreativeSampleRealAssetUseScopeReviewDecisionV1.schema.json": (
        "3bb910d1ed25dd79cc32626ed2c0011c508ecc698771608dbe94352da5707754"
    ),
    "CreativeSampleRealAssetUseScopeReviewRecordV1.schema.json": (
        "c6453c24fd541505b3873a99a7e907b39437964df008203a298190de764fc4b8"
    ),
}
PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_SCHEMA_SHA256 = {
    **PRE_FRESH_STATUS_V30_SCHEMA_SHA256,
    "CreativeSampleRealAssetFreshStatusSourceObservationV1.schema.json": (
        "42e4c98388e61f4601d48694de3321b1df7d1363c8e81373d182bf7c21c85edf"
    ),
    "CreativeSampleRealAssetFreshStatusRequestV1.schema.json": (
        "1ed275c92bf6d85fe2cec086bb9f28c3a9e54b2da4efacb7f5e7290ad7ff4e56"
    ),
    "CreativeSampleRealAssetFreshStatusInstructionV1.schema.json": (
        "0a3834758f907c975f8ae3cb83609b19549d4178b4d957848864f9b1b6ad2163"
    ),
    "CreativeSampleRealAssetFreshStatusDecisionV1.schema.json": (
        "5ac58dbb91dc521528f32257a1e361ca30b2f4810a43aff25996314e42127507"
    ),
    "CreativeSampleRealAssetFreshStatusEvidenceRecordV1.schema.json": (
        "6d9d5c210ffa2ba6bbaa9ab5d24dc3251827026b214df0d1eb9ef55a90a20b78"
    ),
    "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.schema.json": (
        "e833c5a707569ff413a068076794feca71d8f757ae9d30ae257595b24049352b"
    ),
}
PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_MODEL_NAMES = (
    "StoryInput",
    "NIR",
    "PIR",
    "AudioMasterClock",
    "JobGraph",
    "GenerationJob",
    "AssemblyPlan",
    "CharacterAssetVersion",
    "CharacterBible",
    "SceneAssetVersion",
    "SceneBible",
    "DialogueLine",
    "CreativeSampleShotSpec",
    "CreativeSampleSpec",
    "NIRSceneV2",
    "NIRV2",
    "CharacterAssetBinding",
    "StoryboardShotV2",
    "PIRV2",
    "CreativeSampleMetrics",
    "CreativeSampleCompilation",
    "RunEvent",
    "QCReport",
    "QCEvidence",
    "ReleaseManifest",
    "ProviderProfile",
    "ProviderRequest",
    "ProviderSubmission",
    "ProviderTaskSnapshot",
    "DownloadedArtifact",
    "ProviderFailure",
    "CancelResult",
    "ProviderCapabilitySnapshot",
    "ProviderPricingSnapshot",
    "ArkCanaryEntitlementSnapshot",
    "LiveAuthorization",
    "CanaryPlan",
    "EvidenceBoundCanaryPlan",
    "EvidenceBoundLiveAuthorization",
    "CanaryExecution",
    "EvidenceBundle",
    "CreativeSamplePilotSpecDocument",
    "CreativeSamplePilotPack",
    "CreativeSampleRealAssetIntakeTemplate",
    "CreativeSampleRealAssetSubmission",
    "CreativeSampleRealAssetGapReport",
    "CreativeSampleFrozenRealAssetPackManifest",
    "CreativeSampleRealAssetRightsManifest",
    "CreativeSampleRealAssetSpecDocument",
    "CreativeSampleRealAssetRevision",
    "CreativeSampleRealAssetRightsEvidenceBundleV2",
    "CreativeSampleRealAssetHumanPackReviewV2",
    "CreativeSampleRealAssetReviewPairCheckV2",
    "CreativeSampleRealAssetQualificationRequestV2",
    "CreativeSampleRealAssetQualificationDecisionV2",
    "CreativeSampleRealAssetQualificationDecisionInstructionV22",
    "CreativeSampleRealAssetRightsManifestV2",
    "CreativeSampleRealAssetUsePlanV1",
    "CreativeSampleRealAssetUseScopeReviewRequestV1",
    "CreativeSampleRealAssetUseScopeReviewInstructionV1",
    "CreativeSampleRealAssetUseScopeReviewDecisionV1",
    "CreativeSampleRealAssetUseScopeReviewRecordV1",
    "CreativeSampleRealAssetFreshStatusSourceObservationV1",
    "CreativeSampleRealAssetFreshStatusRequestV1",
    "CreativeSampleRealAssetFreshStatusInstructionV1",
    "CreativeSampleRealAssetFreshStatusDecisionV1",
    "CreativeSampleRealAssetFreshStatusEvidenceRecordV1",
    "CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1",
)

# The approved Windows checkout observations over raw CRLF bytes were
# b169a809cba261c9930b624c935723ebbcd8bf95e7d8b837062c7afe3baf7c27 and
# b9e8af2091dde873274d1d98e833cad04ddc9d2743bfe80d31add6f5baf39828.
# Committed Schema identity follows the cross-platform canonical-LF/Git-blob policy.
PRE_REFERENCE_PROMPT_COMPILER_SCHEMA_SHA256 = {
    **PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_SCHEMA_SHA256,
    "CreativeSampleVisualPromptCompileRequestV1.schema.json": (
        "c3d2f61840ff2f1214b638e746ec3d9ca3ee9decbc74cc75a38e88449e7b1bf5"
    ),
    "CreativeSampleVisualPromptSidecarV1.schema.json": (
        "00cb4984018c261d2aed99753f149107bace1b5f19c5fcc3d6831e8c599edfae"
    ),
}
PRE_REFERENCE_PROMPT_COMPILER_MODEL_NAMES = (
    *PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_MODEL_NAMES,
    "CreativeSampleVisualPromptCompileRequestV1",
    "CreativeSampleVisualPromptSidecarV1",
)
PRE_GENERATED_REFERENCE_CANDIDATE_SCHEMA_SHA256 = {
    **PRE_REFERENCE_PROMPT_COMPILER_SCHEMA_SHA256,
    "CreativeSampleReferenceVisualPromptCompileRequestV1.schema.json": (
        "79ffb526cbfc238615d957c802cc92ed40d03a5d10ca57d93030981b3a3dc44d"
    ),
    "CreativeSampleReferenceVisualPromptArtifactV1.schema.json": (
        "0c14d51539bd778fb6ab5c97f1075011701688f5b3035314e41d1b5c71aedad9"
    ),
}
PRE_GENERATED_REFERENCE_CANDIDATE_MODEL_NAMES = (
    *PRE_REFERENCE_PROMPT_COMPILER_MODEL_NAMES,
    "CreativeSampleReferenceVisualPromptCompileRequestV1",
    "CreativeSampleReferenceVisualPromptArtifactV1",
)
PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_SCHEMA_SHA256 = {
    **PRE_GENERATED_REFERENCE_CANDIDATE_SCHEMA_SHA256,
    "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.schema.json": (
        "5c26b4755967f276038a60e725965497b53384d406989e1b186e27701cb4ce88"
    ),
    "CreativeSampleGeneratedReferenceCandidateV1.schema.json": (
        "58a322669c7aeec8dcefafafdffea11757cfd3512a40acccf56722be5f5fd565"
    ),
    "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1.schema.json": (
        "192e41657d55a4d48287938462a323071cb5678fcc521d01edab16ee88d652dd"
    ),
    "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1.schema.json": (
        "fe38cc03c0544e49bb08ca00827df80fbba01e5541479bcf5b49599bc513c0e1"
    ),
}
PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_MODEL_NAMES = (
    *PRE_GENERATED_REFERENCE_CANDIDATE_MODEL_NAMES,
    "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1",
    "CreativeSampleGeneratedReferenceCandidateV1",
    "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1",
    "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1",
)
PRE_GENERATED_REFERENCE_ASSET_PROMOTION_SCHEMA_SHA256 = {
    **PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_SCHEMA_SHA256,
    "CreativeSampleGeneratedReferenceRightsManifestV1.schema.json": (
        "803b68a355ffcd3e1e568e9500775228f50f1752bbf2d3bc884c8142295ba390"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1.schema.json": (
        "2c32b196c8f1c10236421a84f013d529bb8c7b143f692da3127b1c26e8df3d3c"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusRequestV1.schema.json": (
        "ad44e9c9eb278996268e8da1443c623ca2ee385b74eae65b1338c6546b0b2dbf"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1.schema.json": (
        "d0a507565f00865e6a3b3816a23e897d1fb3e890ecb53025fb19c88b609928f7"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1.schema.json": (
        "2e9a34b966c6e19eb4cb44f8f592ab59e3a79539e1ca688827051fbc56b2c11e"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1.schema.json": (
        "aeb01a253c85c32ef19d072e5514bd7d7b9d9377f6f54a737ff298546f2101c5"
    ),
    "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1.schema.json": (
        "241fa5451c153998abd3d918f7e2221eb5bb504cfaf0286b165de2221d74173b"
    ),
}
PRE_GENERATED_REFERENCE_ASSET_PROMOTION_MODEL_NAMES = (
    *PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_MODEL_NAMES,
    "CreativeSampleGeneratedReferenceRightsManifestV1",
    "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1",
    "CreativeSampleGeneratedReferenceCurrentStatusRequestV1",
    "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1",
    "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1",
    "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1",
    "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1",
)


def test_pre_v2_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_V2_SCHEMA_SHA256) == 50
    for name, digest in PRE_V2_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_qualification_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_QUALIFICATION_SCHEMA_SHA256) == 53
    for name, digest in PRE_QUALIFICATION_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_request_preparer_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_REQUEST_PREPARER_SCHEMA_SHA256) == 55
    for name, digest in PRE_REQUEST_PREPARER_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_instruction_preparer_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_INSTRUCTION_PREPARER_SCHEMA_SHA256) == 56
    for name, digest in PRE_INSTRUCTION_PREPARER_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_manifest_finalizer_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_MANIFEST_FINALIZER_SCHEMA_SHA256) == 57
    for name, digest in PRE_MANIFEST_FINALIZER_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_fresh_status_v30_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_FRESH_STATUS_V30_SCHEMA_SHA256) == 62
    for name, digest in PRE_FRESH_STATUS_V30_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_visual_prompt_compiler_integration_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_SCHEMA_SHA256) == 68
    assert len(PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_MODEL_NAMES) == 68
    assert tuple(model.__name__ for model in MODELS[:68]) == (
        PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_MODEL_NAMES
    )
    expected_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:68]}
    assert set(PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_SCHEMA_SHA256) == expected_prefix
    for name, digest in PRE_VISUAL_PROMPT_COMPILER_INTEGRATION_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_reference_prompt_compiler_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_REFERENCE_PROMPT_COMPILER_SCHEMA_SHA256) == 70
    assert len(PRE_REFERENCE_PROMPT_COMPILER_MODEL_NAMES) == 70
    assert tuple(model.__name__ for model in MODELS[:70]) == (
        PRE_REFERENCE_PROMPT_COMPILER_MODEL_NAMES
    )
    expected_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:70]}
    assert set(PRE_REFERENCE_PROMPT_COMPILER_SCHEMA_SHA256) == expected_prefix
    for name, digest in PRE_REFERENCE_PROMPT_COMPILER_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_generated_reference_candidate_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_GENERATED_REFERENCE_CANDIDATE_SCHEMA_SHA256) == 72
    assert len(PRE_GENERATED_REFERENCE_CANDIDATE_MODEL_NAMES) == 72
    assert tuple(model.__name__ for model in MODELS[:72]) == (
        PRE_GENERATED_REFERENCE_CANDIDATE_MODEL_NAMES
    )
    expected_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:72]}
    assert set(PRE_GENERATED_REFERENCE_CANDIDATE_SCHEMA_SHA256) == expected_prefix
    for name, digest in PRE_GENERATED_REFERENCE_CANDIDATE_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_generated_reference_rights_current_status_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_SCHEMA_SHA256) == 76
    assert len(PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_MODEL_NAMES) == 76
    assert tuple(model.__name__ for model in MODELS[:76]) == (
        PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_MODEL_NAMES
    )
    expected_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:76]}
    assert set(PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_SCHEMA_SHA256) == expected_prefix
    for name, digest in PRE_GENERATED_REFERENCE_RIGHTS_CURRENT_STATUS_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_all_pre_generated_reference_asset_promotion_schema_bytes_remain_unchanged() -> None:
    assert len(PRE_GENERATED_REFERENCE_ASSET_PROMOTION_SCHEMA_SHA256) == 83
    assert len(PRE_GENERATED_REFERENCE_ASSET_PROMOTION_MODEL_NAMES) == 83
    assert tuple(model.__name__ for model in MODELS[:83]) == (
        PRE_GENERATED_REFERENCE_ASSET_PROMOTION_MODEL_NAMES
    )
    expected_prefix = {f"{model.__name__}.schema.json" for model in MODELS[:83]}
    assert set(PRE_GENERATED_REFERENCE_ASSET_PROMOTION_SCHEMA_SHA256) == expected_prefix
    for name, digest in PRE_GENERATED_REFERENCE_ASSET_PROMOTION_SCHEMA_SHA256.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest, name


def test_schema_model_names_are_unique_and_match_committed_files() -> None:
    from sdc.real_asset_fresh_status_record_as_of_assessment_receipt_v30 import (
        CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1,
    )

    model_names = [model.__name__ for model in MODELS]
    assert len(model_names) == 86
    assert len(model_names) == len(set(model_names))
    assert MODELS[67] is CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1
    assert [model.__name__ for model in MODELS[68:70]] == [
        "CreativeSampleVisualPromptCompileRequestV1",
        "CreativeSampleVisualPromptSidecarV1",
    ]
    assert [model.__name__ for model in MODELS[70:72]] == [
        "CreativeSampleReferenceVisualPromptCompileRequestV1",
        "CreativeSampleReferenceVisualPromptArtifactV1",
    ]
    assert [model.__name__ for model in MODELS[72:76]] == [
        "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1",
        "CreativeSampleGeneratedReferenceCandidateV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1",
    ]
    assert [model.__name__ for model in MODELS[76:83]] == [
        "CreativeSampleGeneratedReferenceRightsManifestV1",
        "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1",
        "CreativeSampleGeneratedReferenceCurrentStatusRequestV1",
        "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1",
        "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1",
        "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1",
        "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1",
    ]
    assert [model.__name__ for model in MODELS[83:86]] == [
        "CreativeSampleGeneratedReferenceAssetPromotionRequestV1",
        "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1",
        "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1",
    ]
    assert (
        model_names.count(CreativeSampleRealAssetFreshStatusRecordAsOfAssessmentReceiptV1.__name__)
        == 1
    )

    expected = {f"{name}.schema.json" for name in model_names}
    committed = {path.name for path in Path("schemas").glob("*.schema.json")}
    assert committed == expected


def test_generated_reference_candidate_schemas_are_closed_and_all_fields_required() -> None:
    schema_names = (
        "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1",
        "CreativeSampleGeneratedReferenceCandidateV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1",
    )
    schemas = {
        name: json.loads(Path(f"schemas/{name}.schema.json").read_text())
        for name in schema_names
    }
    expected_top_level_fields = {
        "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1": 65,
        "CreativeSampleGeneratedReferenceCandidateV1": 68,
        "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1": 46,
        "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1": 53,
    }
    expected_inline_definitions = {
        "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1": {
            "GeneratedReferenceOutputDescriptorV1",
            "GeneratedReferencePngTechnicalRecordV1",
        },
        "CreativeSampleGeneratedReferenceCandidateV1": set(),
        "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1": {
            "GeneratedReferenceQualificationEvidenceReferenceV1"
        },
        "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1": {
            "GeneratedReferenceQualificationGateResultV1"
        },
    }

    for name, expected_count in expected_top_level_fields.items():
        schema = schemas[name]
        assert schema["additionalProperties"] is False
        assert len(schema["properties"]) == expected_count
        assert len(schema["required"]) == expected_count
        assert set(schema["required"]) == set(schema["properties"])
        assert set(schema.get("$defs", {})) == expected_inline_definitions[name]
        declared_objects = {"<root>": schema, **schema.get("$defs", {})}
        for object_name, object_schema in declared_objects.items():
            if object_schema.get("type") != "object" or "properties" not in object_schema:
                continue
            assert object_schema.get("additionalProperties") is False, (name, object_name)
            assert set(object_schema.get("required", ())) == set(object_schema["properties"]), (
                name,
                object_name,
            )

    inline_definitions = set().union(*expected_inline_definitions.values())
    registered_names = {model.__name__ for model in MODELS}
    assert inline_definitions.isdisjoint(registered_names)
    assert not any(
        (Path("schemas") / f"{name}.schema.json").exists() for name in inline_definitions
    )


def test_generated_reference_rights_status_schemas_are_closed_and_all_fields_required() -> None:
    schema_names = (
        "CreativeSampleGeneratedReferenceRightsManifestV1",
        "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1",
        "CreativeSampleGeneratedReferenceCurrentStatusRequestV1",
        "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1",
        "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1",
        "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1",
        "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1",
    )
    schemas = {
        name: json.loads(Path(f"schemas/{name}.schema.json").read_text())
        for name in schema_names
    }
    expected_top_level_fields = {
        "CreativeSampleGeneratedReferenceRightsManifestV1": 78,
        "CreativeSampleGeneratedReferenceCurrentStatusSourceObservationV1": 49,
        "CreativeSampleGeneratedReferenceCurrentStatusRequestV1": 38,
        "CreativeSampleGeneratedReferenceCurrentStatusInstructionV1": 43,
        "CreativeSampleGeneratedReferenceCurrentStatusDecisionV1": 44,
        "CreativeSampleGeneratedReferenceCurrentStatusEvidenceRecordV1": 35,
        "CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1": 56,
    }
    inline_definitions = {
        "GeneratedReferenceRightsManifestEvidenceReferenceV1",
        "GeneratedReferenceRightsManifestGateResultV1",
        "GeneratedReferenceRightsScopeProposalV1",
        "GeneratedReferenceReviewedRightsScopeV1",
        "GeneratedReferenceCurrentStatusSubjectClosureV1",
        "GeneratedReferenceCurrentStatusObservationRefV1",
        "GeneratedReferenceCurrentStatusChainHeadRefV1",
        "GeneratedReferenceCurrentStatusChainLinkV1",
        "GeneratedReferenceCurrentStatusCategoryResultV1",
    }
    zero_authority_literals: dict[str, object] = {
        "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "automated_execution_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
        "grants_rights": False,
        "grants_qualification": False,
        "grants_execution_authority": False,
        "eligible_for_asset_promotion": False,
        "replaces_rights_manifest": False,
        "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    }

    observed_definitions: set[str] = set()
    for name, expected_count in expected_top_level_fields.items():
        schema = schemas[name]
        assert schema["additionalProperties"] is False
        assert len(schema["properties"]) == expected_count
        assert len(schema["required"]) == expected_count
        assert set(schema["required"]) == set(schema["properties"])
        assert schema["properties"]["evidence_scope"]["const"] == (
            "EXPLICIT_FINITE_BOUND_SET_ONLY"
        )
        for field_name, literal in zero_authority_literals.items():
            assert schema["properties"][field_name]["const"] == literal

        definitions = schema.get("$defs", {})
        observed_definitions.update(definitions)
        assert set(definitions) <= inline_definitions | set(schema_names)
        declared_objects = {"<root>": schema, **definitions}
        for object_name, object_schema in declared_objects.items():
            if object_schema.get("type") != "object" or "properties" not in object_schema:
                continue
            assert object_schema.get("additionalProperties") is False, (name, object_name)
            assert set(object_schema.get("required", ())) == set(object_schema["properties"]), (
                name,
                object_name,
            )

    assert inline_definitions <= observed_definitions
    registered_names = {model.__name__ for model in MODELS}
    assert inline_definitions.isdisjoint(registered_names)
    assert not any(
        (Path("schemas") / f"{name}.schema.json").exists() for name in inline_definitions
    )


def test_generated_reference_promotion_schemas_are_closed_and_zero_authority() -> None:
    schema_names = (
        "CreativeSampleGeneratedReferenceAssetPromotionRequestV1",
        "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1",
        "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1",
    )
    schemas = {
        name: json.loads(Path(f"schemas/{name}.schema.json").read_text())
        for name in schema_names
    }
    expected_non_authority_fields = {
        "CreativeSampleGeneratedReferenceAssetPromotionRequestV1": {
            "schema_version",
            "document_type",
            "request_scope",
            "request_id",
            "request_sha256",
            "policy_id",
            "policy_version",
            "policy_document_sha256",
            "promotion_review_payload_sha256",
            "reference_prompt_artifact_sha256",
            "provider_attempt_outcome_id",
            "provider_attempt_outcome_sha256",
            "candidate_id",
            "candidate_sha256",
            "output_ordinal",
            "media_type",
            "media_content_sha256",
            "media_size_bytes",
            "media_technical_record_sha256",
            "qualification_request_id",
            "qualification_request_sha256",
            "qualification_decision_id",
            "qualification_decision_sha256",
            "qualification_decision_at",
            "qualification_valid_until",
            "manifest_id",
            "manifest_sha256",
            "manifest_at",
            "manifest_valid_until",
            "reviewed_rights_scope",
            "status_subject_closure_id",
            "status_subject_closure_sha256",
            "requested_status_record_id",
            "requested_status_record_sha256",
            "requested_status_receipt_id",
            "requested_status_receipt_sha256",
            "requested_explicit_chain_set_sha256",
            "requested_coverage_set_sha256",
            "requested_joint_replay_sha256",
            "requested_as_of_assessment_sha256",
            "requested_as_of",
            "requested_as_of_status",
            "requested_status_valid_until",
            "requested_primary_asset_binding",
            "maker_identity_ref_sha256",
            "maker_action_sha256",
            "maker_prepared_at",
            "requested_at",
            "request_valid_until",
            "request_basis",
            "requested_representation",
            "composite_media_unsplit",
            "role_assignment_embedded",
            "bible_mutation_requested",
            "provider_input_requested",
            "promotion_performed",
            "sidecar_materialized",
            "eligible_for_separate_role_binding_review",
            "status",
            "evidence_scope",
        },
        "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1": {
            "schema_version",
            "document_type",
            "decision_scope",
            "decision_id",
            "decision_sha256",
            "policy_id",
            "policy_version",
            "policy_document_sha256",
            "promotion_review_payload_sha256",
            "request_id",
            "request_sha256",
            "reference_prompt_artifact_sha256",
            "provider_attempt_outcome_id",
            "provider_attempt_outcome_sha256",
            "candidate_id",
            "candidate_sha256",
            "media_content_sha256",
            "qualification_request_id",
            "qualification_request_sha256",
            "qualification_decision_id",
            "qualification_decision_sha256",
            "qualification_valid_until",
            "manifest_id",
            "manifest_sha256",
            "manifest_valid_until",
            "reviewed_rights_scope",
            "requested_primary_asset_binding",
            "promotion_primary_asset_binding",
            "status_subject_closure_id",
            "status_subject_closure_sha256",
            "promotion_status_record_id",
            "promotion_status_record_sha256",
            "promotion_status_receipt_id",
            "promotion_status_receipt_sha256",
            "promotion_explicit_chain_set_sha256",
            "promotion_coverage_set_sha256",
            "promotion_joint_replay_sha256",
            "promotion_as_of_assessment_sha256",
            "promotion_as_of_status",
            "promotion_status_valid_until",
            "checker_identity_ref_sha256",
            "checker_action_sha256",
            "checker_reviewed_at",
            "decision_at",
            "promotion_at",
            "gate_results",
            "promotion_issue_codes",
            "promotion_basis",
            "decision",
            "sidecar_materialization_allowed",
            "promotion_review_performed",
            "sidecar_id_embedded",
            "role_assignment_embedded",
            "provider_input_eligible",
            "status",
            "evidence_scope",
        },
        "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1": {
            "schema_version",
            "document_type",
            "sidecar_scope",
            "sidecar_id",
            "sidecar_sha256",
            "policy_id",
            "policy_version",
            "policy_document_sha256",
            "request_id",
            "request_sha256",
            "decision_id",
            "decision_sha256",
            "reference_prompt_artifact_sha256",
            "provider_attempt_outcome_id",
            "provider_attempt_outcome_sha256",
            "candidate_id",
            "candidate_sha256",
            "output_ordinal",
            "media_type",
            "media_content_sha256",
            "media_size_bytes",
            "media_technical_record_sha256",
            "qualification_request_id",
            "qualification_request_sha256",
            "qualification_decision_id",
            "qualification_decision_sha256",
            "qualification_valid_until",
            "manifest_id",
            "manifest_sha256",
            "manifest_valid_until",
            "reviewed_rights_scope",
            "primary_asset_binding",
            "status_subject_closure_id",
            "status_subject_closure_sha256",
            "promotion_status_record_id",
            "promotion_status_record_sha256",
            "promotion_status_receipt_id",
            "promotion_status_receipt_sha256",
            "promotion_explicit_chain_set_sha256",
            "promotion_coverage_set_sha256",
            "promotion_joint_replay_sha256",
            "promotion_as_of_assessment_sha256",
            "promotion_as_of_status",
            "promotion_at",
            "promotion_status_valid_until",
            "promotion_evidence_valid_until",
            "origin_claim",
            "origin_assurance",
            "sidecar_state",
            "promotion_performed",
            "eligible_for_separate_role_binding_review",
            "primary_asset_binding_replaced",
            "bible_active_binding_changed",
            "asset_version_v1_created",
            "composite_media_unsplit",
            "role_assignment_embedded",
            "provider_input_eligible",
            "present_currentness_asserted",
            "perpetual_eligibility_asserted",
            "supersedes_sidecar",
            "status",
            "evidence_scope",
        },
    }
    primary_binding_name = "GeneratedReferencePromotionPrimaryAssetBindingV1"
    gate_result_name = "GeneratedReferencePromotionGateResultV1"
    reviewed_rights_scope_name = "GeneratedReferenceReviewedRightsScopeV1"
    expected_inline_definitions = {
        "CreativeSampleGeneratedReferenceAssetPromotionRequestV1": {
            primary_binding_name,
            reviewed_rights_scope_name,
        },
        "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1": {
            primary_binding_name,
            gate_result_name,
            reviewed_rights_scope_name,
        },
        "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1": {
            primary_binding_name,
            reviewed_rights_scope_name,
        },
    }
    expected_primary_binding_fields = {
        "binding_profile",
        "primary_asset_binding_sha256",
        "asset_purpose",
        "subject_id",
        "asset_version_id",
        "legacy_asset_version_projection_sha256",
        "version",
        "content_sha256",
        "media_type",
        "approval_ref",
        "provenance",
        "bible_active_asset_version_id",
    }
    expected_gate_result_fields = {"ordinal", "gate", "result", "basis"}
    zero_authority_literals: dict[str, object] = {
        "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "automated_execution_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
        "grants_rights": False,
        "grants_qualification": False,
        "grants_execution_authority": False,
        "eligible_for_asset_promotion": False,
        "replaces_rights_manifest": False,
        "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    }

    expected_non_authority_counts = {
        "CreativeSampleGeneratedReferenceAssetPromotionRequestV1": 60,
        "CreativeSampleGeneratedReferenceAssetPromotionDecisionV1": 56,
        "CreativeSampleGeneratedReferenceEligibleAssetSidecarV1": 62,
    }
    assert {
        name: len(fields) for name, fields in expected_non_authority_fields.items()
    } == expected_non_authority_counts

    for name, expected_non_authority in expected_non_authority_fields.items():
        schema = schemas[name]
        expected_properties = expected_non_authority | set(zero_authority_literals)
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == expected_properties
        assert set(schema["required"]) == expected_properties
        assert schema["properties"]["evidence_scope"]["const"] == (
            "EXPLICIT_FINITE_BOUND_SET_ONLY"
        )
        assert set(zero_authority_literals) <= set(schema["required"])
        for field_name, literal in zero_authority_literals.items():
            assert schema["properties"][field_name]["const"] == literal

        definitions = schema.get("$defs", {})
        assert set(definitions) == expected_inline_definitions[name]
        primary_binding = definitions[primary_binding_name]
        assert set(primary_binding["properties"]) == expected_primary_binding_fields
        if gate_result_name in expected_inline_definitions[name]:
            gate_result = definitions[gate_result_name]
            assert set(gate_result["properties"]) == expected_gate_result_fields

        declared_objects = {"<root>": schema, **definitions}
        for object_name, object_schema in declared_objects.items():
            if object_schema.get("type") != "object" or "properties" not in object_schema:
                continue
            assert object_schema.get("additionalProperties") is False, (name, object_name)
            assert set(object_schema.get("required", ())) == set(object_schema["properties"]), (
                name,
                object_name,
            )

    inline_definitions = {
        primary_binding_name,
        gate_result_name,
        reviewed_rights_scope_name,
    }
    registered_names = {model.__name__ for model in MODELS}
    assert inline_definitions.isdisjoint(registered_names)
    assert not any(
        (Path("schemas") / f"{name}.schema.json").exists() for name in inline_definitions
    )


def test_reference_prompt_compiler_schemas_are_closed_and_all_fields_required() -> None:
    schema_names = (
        "CreativeSampleReferenceVisualPromptCompileRequestV1",
        "CreativeSampleReferenceVisualPromptArtifactV1",
    )
    schemas = {
        name: json.loads(Path(f"schemas/{name}.schema.json").read_text()) for name in schema_names
    }

    expected_top_level_fields = {
        "CreativeSampleReferenceVisualPromptCompileRequestV1": 38,
        "CreativeSampleReferenceVisualPromptArtifactV1": 41,
    }
    for name, expected_count in expected_top_level_fields.items():
        schema = schemas[name]
        assert schema["additionalProperties"] is False
        assert len(schema["properties"]) == expected_count
        assert len(schema["required"]) == expected_count
        assert set(schema["required"]) == set(schema["properties"])

    artifact_schema = schemas["CreativeSampleReferenceVisualPromptArtifactV1"]
    closed_inline_definitions = {
        "_CharacterReferenceSourceV1",
        "_SceneReferenceSourceV1",
        "_CharacterVisualPromptProfileSnapshotV1",
        "_SceneVisualPromptProfileSnapshotV1",
        "_CharacterReferenceAssetRecipeV1",
        "_SceneReferenceAssetRecipeV1",
        "_CharacterReferencePromptRenderInputV1",
        "_SceneReferencePromptRenderInputV1",
        "_PromptRenderReceiptV1",
    }
    assert closed_inline_definitions <= set(artifact_schema["$defs"])
    receipt_schema = artifact_schema["$defs"]["_PromptRenderReceiptV1"]
    assert len(receipt_schema["properties"]) == 32
    assert len(receipt_schema["required"]) == 32

    request_definitions = schemas["CreativeSampleReferenceVisualPromptCompileRequestV1"]["$defs"]
    for source_name in ("_CharacterReferenceSourceV1", "_SceneReferenceSourceV1"):
        source_properties = request_definitions[source_name]["properties"]
        assert source_properties["narrative"]["minLength"] == 1
        assert source_properties["narrative"]["maxLength"] == 4000
        assert source_properties["action"]["minLength"] == 1
        assert source_properties["action"]["maxLength"] == 2000
    props_schema = request_definitions["_SceneReferenceSourceV1"]["properties"]["props"]
    assert props_schema["minItems"] == 0
    assert props_schema["maxItems"] == 16
    assert props_schema["uniqueItems"] is True
    assert props_schema["items"]["minLength"] == 1
    assert props_schema["items"]["maxLength"] == 128

    character_input = artifact_schema["$defs"]["_CharacterReferencePromptRenderInputV1"]
    for map_name in ("emotion_by_character", "wardrobe_by_character"):
        map_schema = character_input["properties"][map_name]
        assert map_schema["minProperties"] == 1
        assert map_schema["maxProperties"] == 1
        assert map_schema["additionalProperties"] is False
        assert len(map_schema["patternProperties"]) == 1
    assert character_input["properties"]["character_asset_bindings"]["minItems"] == 1
    assert character_input["properties"]["character_asset_bindings"]["maxItems"] == 1

    character_snapshot = artifact_schema["$defs"]["_CharacterVisualPromptProfileSnapshotV1"]
    scene_snapshot = artifact_schema["$defs"]["_SceneVisualPromptProfileSnapshotV1"]
    assert character_snapshot["properties"]["reference_asset_types"]["minItems"] == 3
    assert character_snapshot["properties"]["reference_asset_types"]["maxItems"] == 3
    assert len(character_snapshot["properties"]["reference_asset_types"]["prefixItems"]) == 3
    assert scene_snapshot["properties"]["reference_asset_types"]["minItems"] == 4
    assert scene_snapshot["properties"]["reference_asset_types"]["maxItems"] == 4
    assert len(scene_snapshot["properties"]["reference_asset_types"]["prefixItems"]) == 4

    for schema_name, schema in schemas.items():
        declared_objects = {"<root>": schema, **schema.get("$defs", {})}
        for object_name, object_schema in declared_objects.items():
            if object_schema.get("type") != "object" or "properties" not in object_schema:
                continue
            assert object_schema.get("additionalProperties") is False, (
                schema_name,
                object_name,
            )
            assert set(object_schema.get("required", ())) == set(object_schema["properties"]), (
                schema_name,
                object_name,
            )


def test_committed_schemas_have_not_drifted() -> None:
    for model in MODELS:
        committed = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        assert committed == model.model_json_schema(), f"schema drift: {model.__name__}"


def test_qualification_v2_schemas_are_append_only_and_zero_authority() -> None:
    assert CreativeSampleRealAssetQualificationRequestV2 in MODELS
    assert CreativeSampleRealAssetQualificationDecisionV2 in MODELS

    expected_constants = {
        "policy_document_sha256": QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
        "rights_manifest_created": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    for model, performed in (
        (CreativeSampleRealAssetQualificationRequestV2, False),
        (CreativeSampleRealAssetQualificationDecisionV2, True),
    ):
        schema = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        properties = schema["properties"]
        for field, expected in expected_constants.items():
            assert properties[field]["const"] == expected
        assert properties["rights_qualification_performed"]["const"] is performed


def test_decision_instruction_v22_schema_is_append_only_and_zero_authority() -> None:
    assert CreativeSampleRealAssetQualificationDecisionInstructionV22 in MODELS
    schema = json.loads(
        Path(
            "schemas/CreativeSampleRealAssetQualificationDecisionInstructionV22.schema.json"
        ).read_text()
    )
    properties = schema["properties"]
    expected_constants = {
        "schema_version": "2.2.0",
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "qualifier_role": "INDEPENDENT_QUALIFIER",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "eligible_for_separate_manifest_design_review": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    for field, expected in expected_constants.items():
        assert properties[field]["const"] == expected


def test_rights_manifest_v2_schema_is_append_only_and_zero_authority() -> None:
    assert CreativeSampleRealAssetRightsManifestV2 in MODELS
    schema = json.loads(
        Path("schemas/CreativeSampleRealAssetRightsManifestV2.schema.json").read_text()
    )
    properties = schema["properties"]
    expected_constants = {
        "schema_version": "2.4.0",
        "document_type": "sdc.creative-sample-real-asset-rights-manifest-v2",
        "qualification_decision": "PASS_ASSET_INTAKE_ONLY",
        "qualification_scope": "ASSET_INTAKE_ONLY",
        "eligible_for_separate_manifest_design_review": True,
        "status": "RIGHTS_MANIFEST_CREATED",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    for field, expected in expected_constants.items():
        assert properties[field]["const"] == expected


def test_use_plan_v1_schema_is_append_only_and_zero_authority() -> None:
    assert CreativeSampleRealAssetUsePlanV1 in MODELS
    schema = json.loads(Path("schemas/CreativeSampleRealAssetUsePlanV1.schema.json").read_text())
    properties = schema["properties"]
    expected_constants = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-use-plan-v1",
        "plan_policy_document_sha256": USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        "source_mode": "IMPORTED_MEDIA",
        "consumer_scope": "OFFLINE_DESIGN_REVIEW_ONLY",
        "shot_count": 10,
        "proposed_attempts_per_shot": 2,
        "proposed_provider_requests_max": 20,
        "proposed_image_generation_requests": 0,
        "proposed_audio_generation_requests": 0,
        "proposed_cost_ceiling_cny": 450,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "status": "USE_PLAN_CANDIDATE_CREATED",
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
    for field, expected in expected_constants.items():
        assert properties[field]["const"] == expected


def test_use_scope_review_v1_schemas_are_partitioned_and_zero_authority() -> None:
    module_models = (
        CreativeSampleRealAssetUseScopeReviewRequestV1,
        CreativeSampleRealAssetUseScopeReviewInstructionV1,
        CreativeSampleRealAssetUseScopeReviewDecisionV1,
    )
    for model in (*module_models, CreativeSampleRealAssetUseScopeReviewRecordV1):
        assert model in MODELS

    expected_zero_authority = {
        "review_policy_document_sha256": USE_SCOPE_REVIEW_V1_POLICY_DOCUMENT_SHA256,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_separate_provider_approval": False,
        "provider_approval_granted": False,
        "eligible_for_real_generation": False,
        "generation_authorized": False,
        "execution_authorized": False,
        "publication_authorized": False,
        "remote_processing_allowed": False,
        "retention_allowed": False,
        "training_allowed": False,
        "publication_allowed": False,
        "authorized_attempts": 0,
        "authorized_cost_cny": 0,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    for model in module_models:
        schema = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        properties = schema["properties"]
        for field, expected in expected_zero_authority.items():
            assert properties[field]["const"] == expected

    record_schema = json.loads(
        Path("schemas/CreativeSampleRealAssetUseScopeReviewRecordV1.schema.json").read_text()
    )
    record_properties = record_schema["properties"]
    assert record_properties["request"]["$ref"].endswith(
        "/CreativeSampleRealAssetUseScopeReviewRequestV1"
    )
    assert record_properties["instruction"]["$ref"].endswith(
        "/CreativeSampleRealAssetUseScopeReviewInstructionV1"
    )
    assert record_properties["decision"]["$ref"].endswith(
        "/CreativeSampleRealAssetUseScopeReviewDecisionV1"
    )
    assert {
        "request_sha256",
        "instruction_sha256",
        "decision_sha256",
    } <= set(record_properties)


def test_fresh_status_v1_schemas_are_registered_partitioned_and_zero_authority() -> None:
    module_models = (
        CreativeSampleRealAssetFreshStatusRequestV1,
        CreativeSampleRealAssetFreshStatusInstructionV1,
        CreativeSampleRealAssetFreshStatusDecisionV1,
    )
    all_models = (
        CreativeSampleRealAssetFreshStatusSourceObservationV1,
        *module_models,
        CreativeSampleRealAssetFreshStatusEvidenceRecordV1,
    )
    for model in all_models:
        assert model in MODELS

    expected_zero_authority = {
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
        "automated_execution_allowed": False,
        "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
    }
    for model in all_models:
        schema = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        properties = schema["properties"]
        for field, expected in expected_zero_authority.items():
            assert properties[field]["const"] == expected

    record_schema = json.loads(
        Path("schemas/CreativeSampleRealAssetFreshStatusEvidenceRecordV1.schema.json").read_text()
    )
    record_properties = record_schema["properties"]
    assert record_properties["request"]["$ref"].endswith(
        "/CreativeSampleRealAssetFreshStatusRequestV1"
    )
    assert record_properties["instruction"]["$ref"].endswith(
        "/CreativeSampleRealAssetFreshStatusInstructionV1"
    )
    assert record_properties["decision"]["$ref"].endswith(
        "/CreativeSampleRealAssetFreshStatusDecisionV1"
    )
    assert {
        "request_sha256",
        "instruction_sha256",
        "decision_sha256",
    } <= set(record_properties)


def test_evidence_bound_authorization_has_a_distinct_committed_schema() -> None:
    assert EvidenceBoundLiveAuthorization in MODELS
    schema = json.loads(Path("schemas/EvidenceBoundLiveAuthorization.schema.json").read_text())
    assert schema["properties"]["document_type"]["const"] == (
        "sdc.evidence-bound-live-authorization"
    )
    assert schema["properties"]["max_posts"]["const"] == 1
    assert schema["properties"]["attempt"]["const"] == 1


def test_legacy_canary_schema_bytes_remain_unchanged() -> None:
    expected = {
        "CanaryPlan.schema.json": (
            "63cc1b14fdd34ecbf80a3693e097b29f9bc79d64015ab001f891cb29a90366bf"
        ),
        "LiveAuthorization.schema.json": (
            "d18d571c9ff374a1ce128de9b005d0aaff02d61de8b7f456c37f16089f0ec6ce"
        ),
    }
    for name, digest in expected.items():
        canonical_lf = (Path("schemas") / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(canonical_lf).hexdigest() == digest


def test_provider_failure_1_0_0_payload_remains_backward_compatible() -> None:
    legacy_payload = {
        "schema_version": "1.0.0",
        "failure_class": "REMOTE_FAILED",
        "code": "legacy provider code with spaces / ? &",
        "message": "legacy first line\n" + "x" * 300,
        "retryable": True,
    }

    failure = ProviderFailure.model_validate(legacy_payload)

    assert failure.model_dump(mode="json") == legacy_payload
    expected_fields = {"schema_version", "failure_class", "code", "message", "retryable"}
    assert set(ProviderFailure.model_fields) == expected_fields
    assert set(ProviderFailure.model_json_schema()["properties"]) == expected_fields


def test_provider_pricing_1_0_0_legacy_cost_remains_parseable() -> None:
    legacy_payload = {
        "schema_version": "1.0.0",
        "snapshot_revision": "2026-08-13.v02-r6",
        "status": "CURRENT",
        "provider": "volcengine_ark",
        "model": "doubao-seedance-2-0-260128",
        "resolution": "1080p",
        "input_mode": "WITHOUT_VIDEO",
        "currency": "CNY",
        "billing_unit": "provider-token",
        "unit_price_cny": "0.000051",
        "worst_case_units": "194400",
        "worst_case_cost_cny": "9.9144",
        "source_url": "https://docs.volcengine.com/docs/82379/1544106",
        "source_updated_at": "2026-08-12T22:01:30+08:00",
        "captured_at": "2026-08-13T17:14:11+08:00",
        "valid_until": "2026-08-13T23:59:59+08:00",
        "evidence_sha256": "a" * 64,
    }

    snapshot = ProviderPricingSnapshot.model_validate(legacy_payload)

    assert snapshot.worst_case_units == Decimal("194400")
    assert snapshot.worst_case_cost_cny == Decimal("9.9144")
    expected_fields = {
        "schema_version",
        "snapshot_revision",
        "status",
        "provider",
        "model",
        "resolution",
        "input_mode",
        "currency",
        "billing_unit",
        "unit_price_cny",
        "worst_case_units",
        "worst_case_cost_cny",
        "source_url",
        "source_updated_at",
        "captured_at",
        "valid_until",
        "evidence_sha256",
    }
    assert set(ProviderPricingSnapshot.model_fields) == expected_fields
    assert set(ProviderPricingSnapshot.model_json_schema()["properties"]) == expected_fields
