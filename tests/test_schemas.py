import hashlib
import json
from decimal import Decimal
from pathlib import Path

from sdc.contracts import (
    EvidenceBoundLiveAuthorization,
    ProviderFailure,
    ProviderPricingSnapshot,
)
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
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
    "CanaryPlan.schema.json": (
        "63cc1b14fdd34ecbf80a3693e097b29f9bc79d64015ab001f891cb29a90366bf"
    ),
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
    "JobGraph.schema.json": (
        "17d312d080a7d5d849725cb0c96c1898e090281c2cbb8b826f00a0e3616c9132"
    ),
    "LiveAuthorization.schema.json": (
        "d18d571c9ff374a1ce128de9b005d0aaff02d61de8b7f456c37f16089f0ec6ce"
    ),
    "NIR.schema.json": (
        "ddc2ca8ce2da365724a52c58d175f61ddd86285dcfa08618720e7decda08ad05"
    ),
    "NIRSceneV2.schema.json": (
        "3c67d0a01e106c0a27fcda34d215a66916d9e21479dc60648df1130206b368bc"
    ),
    "NIRV2.schema.json": (
        "6f818b5cddb72b37ea6e424099bc417542fcf638e10e8344346273ff77c2dfae"
    ),
    "PIR.schema.json": (
        "48533b52f1886eee001282efe096591a216b5df8a6d914bfe31b830b8fb4dec4"
    ),
    "PIRV2.schema.json": (
        "38a4c595bb66bd23d6363a638df4b743cbecbba053c54b3e47925fc759b0b034"
    ),
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
    "QCEvidence.schema.json": (
        "fef0d47246737c98a7d8d99ed5fc86fb822485b1cd318300aa4f7a1ccdb9b548"
    ),
    "QCReport.schema.json": (
        "e05f308ea9d0cf82792fe2a910819df0ce01a7b394b9258e4d867b30f0c9f8b6"
    ),
    "ReleaseManifest.schema.json": (
        "5232a09b390cdaed8019b18d58134eb56ece3a9ac01c4419a17c7b4ccc8b44a5"
    ),
    "RunEvent.schema.json": (
        "ebc5626785cee74705f49798de58cb34ce4f18690bba9f894b782c855b14bc76"
    ),
    "SceneAssetVersion.schema.json": (
        "3118c9c20e6c89a854faf2c5b85ebc6e3a903b1a5473b22854ea9293d6282759"
    ),
    "SceneBible.schema.json": (
        "b3902530148acb261976d387a9547d13269c2fb7d793040f8f4712f44813831f"
    ),
    "StoryboardShotV2.schema.json": (
        "1f4060808e92e021701daf0f41fb574c9838af471e18d99da04568ed38160b69"
    ),
    "StoryInput.schema.json": (
        "4042419ae5c3fe068fe3b53105cca8110eb67fb2274ab935dea02c2dffc8b6c5"
    ),
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


def test_schema_model_names_are_unique_and_match_committed_files() -> None:
    model_names = [model.__name__ for model in MODELS]
    assert len(model_names) == 56
    assert len(model_names) == len(set(model_names))

    expected = {f"{name}.schema.json" for name in model_names}
    committed = {path.name for path in Path("schemas").glob("*.schema.json")}
    assert committed == expected


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
