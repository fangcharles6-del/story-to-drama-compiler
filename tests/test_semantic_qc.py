from pathlib import Path

import pytest

from sdc.contracts import StoryboardShotV2
from sdc.semantic_qc import (
    NullSemanticVideoAnalyzer,
    SemanticQCObservation,
    SemanticQCStatus,
    semantic_observation_to_advisory_evidence,
    semantic_qc_request_from_shot,
)


def _shot() -> StoryboardShotV2:
    return StoryboardShotV2.model_construct(
        id="storyboard_shot_v2_0123456789abcdef0123",
        narrative="The character discovers the letter.",
        visual_direction="A medium shot in the office.",
        action="She opens the envelope and freezes.",
        continuity_notes="Keep the blue folder on the desk.",
        props=("blue folder", "envelope"),
    )


def test_request_binds_candidate_digest_to_compiled_shot_intent() -> None:
    request = semantic_qc_request_from_shot(_shot(), candidate_sha256="a" * 64)
    assert request.shot_id == "storyboard_shot_v2_0123456789abcdef0123"
    assert request.action == "She opens the envelope and freezes."
    assert request.props == ("blue folder", "envelope")


@pytest.mark.asyncio
async def test_null_analyzer_is_a_zero_network_noop(tmp_path: Path) -> None:
    request = semantic_qc_request_from_shot(_shot(), candidate_sha256="b" * 64)
    observation = await NullSemanticVideoAnalyzer().analyze(
        request=request,
        media=tmp_path / "missing.mp4",
    )
    assert observation.status is SemanticQCStatus.UNAVAILABLE
    assert observation.recommended_match is None
    assert observation.advisory_only is True
    assert observation.automated_decision_allowed is False


def test_negative_semantic_recommendation_never_becomes_a_qc_failure_or_authority() -> None:
    observation = SemanticQCObservation(
        shot_id="storyboard_shot_v2_0123456789abcdef0123",
        candidate_sha256="c" * 64,
        analyzer_id="example",
        model="example-model-v1",
        status=SemanticQCStatus.OBSERVED,
        summary="The envelope is missing.",
        recommended_match=False,
        confidence_milli=930,
    )
    evidence = semantic_observation_to_advisory_evidence(observation)
    assert evidence.passed is True
    assert evidence.details["recommended_match"] is False
    assert evidence.details["advisory_only"] is True
    assert evidence.details["automated_decision_allowed"] is False
    assert evidence.details["quality_gate_changed"] is False


def test_unavailable_observation_cannot_claim_a_recommendation() -> None:
    with pytest.raises(ValueError, match="cannot carry"):
        SemanticQCObservation(
            shot_id="shot-1",
            candidate_sha256="d" * 64,
            analyzer_id="none",
            model="not-configured",
            status=SemanticQCStatus.UNAVAILABLE,
            summary="Unavailable.",
            recommended_match=True,
            confidence_milli=1000,
        )
