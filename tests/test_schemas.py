import json
from pathlib import Path

from sdc.contracts import ProviderFailure
from sdc.schemas import MODELS


def test_committed_schemas_have_not_drifted() -> None:
    for model in MODELS:
        committed = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        assert committed == model.model_json_schema(), f"schema drift: {model.__name__}"


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
