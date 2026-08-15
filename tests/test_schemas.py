import hashlib
import json
from decimal import Decimal
from pathlib import Path

from sdc.contracts import (
    EvidenceBoundLiveAuthorization,
    ProviderFailure,
    ProviderPricingSnapshot,
)
from sdc.schemas import MODELS


def test_committed_schemas_have_not_drifted() -> None:
    for model in MODELS:
        committed = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        assert committed == model.model_json_schema(), f"schema drift: {model.__name__}"


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
