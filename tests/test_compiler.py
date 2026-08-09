import json
from pathlib import Path

from sdc.compiler import compile_story
from sdc.contracts import StoryInput


def test_compilation_is_deterministic() -> None:
    story = StoryInput.model_validate_json(Path("examples/minimal_story.json").read_text())
    first = compile_story(story)
    second = compile_story(story)
    assert [x.model_dump_json() for x in first] == [x.model_dump_json() for x in second]
    assert first[2].duration_ms == 4000
    assert [s.ordinal for s in first[1].shots] == [0, 1]


def test_compilation_has_no_runtime_timestamp() -> None:
    story = StoryInput.model_validate_json(Path("examples/minimal_story.json").read_text())
    encoded = json.dumps([x.model_dump(mode="json") for x in compile_story(story)])
    assert "occurred_at" not in encoded
