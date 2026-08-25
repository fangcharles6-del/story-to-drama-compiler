"""Provider-neutral semantic video observations that cannot decide a quality gate."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from sdc.contracts import QCEvidence, StoryboardShotV2

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_ANALYZER_ID = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


def _valid_text(value: str, *, max_length: int) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= max_length
        and "\x00" not in value
    )


class SemanticQCStatus(StrEnum):
    FAILED = "FAILED"
    OBSERVED = "OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class SemanticQCRequest:
    shot_id: str
    candidate_sha256: str
    narrative: str
    visual_direction: str
    action: str
    continuity_notes: str
    props: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _PORTABLE_ID.fullmatch(self.shot_id):
            raise ValueError("shot_id must be a portable identifier")
        if not _SHA256.fullmatch(self.candidate_sha256):
            raise ValueError("candidate_sha256 must be lowercase SHA-256")
        for field_name, value in (
            ("narrative", self.narrative),
            ("visual_direction", self.visual_direction),
            ("action", self.action),
            ("continuity_notes", self.continuity_notes),
        ):
            if not _valid_text(value, max_length=4000):
                raise ValueError(f"{field_name} must be canonical non-empty text")
        if type(self.props) is not tuple:
            raise TypeError("props must be an exact tuple")
        if self.props != tuple(sorted(set(self.props))):
            raise ValueError("props must be unique and sorted")
        if any(not _valid_text(prop, max_length=128) for prop in self.props):
            raise ValueError("props must contain canonical printable text")


@dataclass(frozen=True, slots=True)
class SemanticQCObservation:
    shot_id: str
    candidate_sha256: str
    analyzer_id: str
    model: str
    status: SemanticQCStatus
    summary: str
    recommended_match: bool | None
    confidence_milli: int | None
    advisory_only: bool = True
    automated_decision_allowed: bool = False

    def __post_init__(self) -> None:
        if not _PORTABLE_ID.fullmatch(self.shot_id):
            raise ValueError("shot_id must be a portable identifier")
        if not _SHA256.fullmatch(self.candidate_sha256):
            raise ValueError("candidate_sha256 must be lowercase SHA-256")
        if not _ANALYZER_ID.fullmatch(self.analyzer_id):
            raise ValueError("analyzer_id must be a canonical lowercase identifier")
        if not _valid_text(self.model, max_length=256):
            raise ValueError("model must be canonical non-empty text")
        if type(self.status) is not SemanticQCStatus:
            raise TypeError("status must be an exact SemanticQCStatus")
        if not _valid_text(self.summary, max_length=2000):
            raise ValueError("summary must be canonical non-empty text")
        if self.advisory_only is not True or self.automated_decision_allowed is not False:
            raise ValueError("semantic observations are advisory-only and cannot decide a gate")
        if self.status is SemanticQCStatus.OBSERVED:
            if type(self.recommended_match) is not bool:
                raise ValueError("observed results require an exact boolean recommendation")
            if (
                type(self.confidence_milli) is not int
                or not 0 <= self.confidence_milli <= 1000
            ):
                raise ValueError("observed results require confidence_milli in 0..1000")
        elif self.recommended_match is not None or self.confidence_milli is not None:
            raise ValueError("unavailable or failed observations cannot carry a recommendation")


class SemanticVideoAnalyzer(Protocol):
    """Worker-side protocol; concrete adapters may inspect one local candidate."""

    async def analyze(
        self,
        *,
        request: SemanticQCRequest,
        media: Path,
    ) -> SemanticQCObservation: ...


class NullSemanticVideoAnalyzer:
    """Safe default that performs no file read, network call, or semantic inference."""

    async def analyze(
        self,
        *,
        request: SemanticQCRequest,
        media: Path,
    ) -> SemanticQCObservation:
        del media
        return SemanticQCObservation(
            shot_id=request.shot_id,
            candidate_sha256=request.candidate_sha256,
            analyzer_id="none",
            model="not-configured",
            status=SemanticQCStatus.UNAVAILABLE,
            summary="Semantic video analysis is not configured.",
            recommended_match=None,
            confidence_milli=None,
        )


def semantic_qc_request_from_shot(
    shot: StoryboardShotV2,
    *,
    candidate_sha256: str,
) -> SemanticQCRequest:
    """Bind one candidate digest to the exact compiled shot intent."""

    if not isinstance(shot, StoryboardShotV2):
        raise TypeError("shot must be a StoryboardShotV2")
    return SemanticQCRequest(
        shot_id=shot.id,
        candidate_sha256=candidate_sha256,
        narrative=shot.narrative,
        visual_direction=shot.visual_direction,
        action=shot.action,
        continuity_notes=shot.continuity_notes,
        props=shot.props,
    )


def semantic_observation_to_advisory_evidence(
    observation: SemanticQCObservation,
) -> QCEvidence:
    """Record an observation without converting its recommendation into pass/fail authority.

    ``passed=True`` means only that the advisory observation was admitted as evidence.  A
    negative recommendation remains data in ``details`` and does not alter ``qc.verify``.
    """

    if type(observation) is not SemanticQCObservation:
        raise TypeError("observation must be an exact SemanticQCObservation")
    recommendation: str | bool = (
        "UNKNOWN"
        if observation.recommended_match is None
        else observation.recommended_match
    )
    return QCEvidence(
        check=f"semantic_qc_observation_recorded:{observation.shot_id}",
        passed=True,
        details={
            "status": observation.status.value,
            "analyzer_id": observation.analyzer_id,
            "model": observation.model,
            "candidate_sha256": observation.candidate_sha256,
            "recommended_match": recommendation,
            "confidence_milli": (
                -1 if observation.confidence_milli is None else observation.confidence_milli
            ),
            "advisory_only": True,
            "automated_decision_allowed": False,
            "quality_gate_changed": False,
            "summary": observation.summary,
        },
    )


__all__ = [
    "NullSemanticVideoAnalyzer",
    "SemanticQCObservation",
    "SemanticQCRequest",
    "SemanticQCStatus",
    "SemanticVideoAnalyzer",
    "semantic_observation_to_advisory_evidence",
    "semantic_qc_request_from_shot",
]
