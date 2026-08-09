"""Versioned, immutable public contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Final[Literal["1.0.0"]] = "1.0.0"
Ms = Annotated[int, Field(ge=0)]


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0.0"] = SCHEMA_VERSION


class StoryBeat(Contract):
    text: str = Field(min_length=1)
    duration_ms: Annotated[int, Field(gt=0)] = 2000


class StoryInput(Contract):
    title: str = Field(min_length=1)
    beats: tuple[StoryBeat, ...] = Field(min_length=1)
    seed: int = 1


class NIRScene(Contract):
    id: str
    ordinal: int
    narrative: str
    duration_ms: Annotated[int, Field(gt=0)]


class NIR(Contract):
    id: str
    title: str
    scenes: tuple[NIRScene, ...]


class PIRShot(Contract):
    id: str
    scene_id: str
    ordinal: int
    prompt: str
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]


class PIR(Contract):
    id: str
    shots: tuple[PIRShot, ...]


class AudioCue(Contract):
    id: str
    shot_id: str
    start_ms: Ms
    end_ms: Ms


class AudioMasterClock(Contract):
    id: str
    duration_ms: Ms
    sample_rate_hz: Literal[48000] = 48000
    cues: tuple[AudioCue, ...]


class GenerationJob(Contract):
    id: str
    shot_id: str
    prompt: str
    duration_ms: Annotated[int, Field(gt=0)]
    depends_on: tuple[str, ...] = ()
    idempotency_key: str
    max_attempts: Literal[2] = 2


class JobGraph(Contract):
    id: str
    jobs: tuple[GenerationJob, ...]


class AssemblyItem(Contract):
    job_id: str
    start_ms: Ms
    duration_ms: Annotated[int, Field(gt=0)]


class AssemblyPlan(Contract):
    id: str
    clock_id: str
    items: tuple[AssemblyItem, ...]


class RunState(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    STOP_2 = "STOP-2"
    HUMAN_GATE = "HUMAN_GATE"


class RunEvent(Contract):
    id: str
    run_id: str
    event_type: str
    state: RunState
    occurred_at: str
    idempotency_key: str
    payload: dict[str, str | int | bool] = {}


class QCEvidence(Contract):
    check: str
    passed: bool
    details: dict[str, str | int | bool]


class QCReport(Contract):
    id: str
    passed: bool
    evidence: tuple[QCEvidence, ...]
    ffprobe: dict[str, object]


class ReleaseManifest(Contract):
    id: str
    media_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0)]
    duration_ms: Ms
