import json
from pathlib import Path

from sdc.schemas import MODELS


def test_committed_schemas_have_not_drifted() -> None:
    for model in MODELS:
        committed = json.loads(Path(f"schemas/{model.__name__}.schema.json").read_text())
        assert committed == model.model_json_schema(), f"schema drift: {model.__name__}"
