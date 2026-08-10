"""Versioned, immutable public contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
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


class ProviderFailureClass(StrEnum):
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    REMOTE_FAILED = "REMOTE_FAILED"
    EXPIRED = "EXPIRED"
    AUTHENTICATION = "AUTHENTICATION"
    QUOTA = "QUOTA"
    CONFIGURATION = "CONFIGURATION"
    INVALID_INPUT = "INVALID_INPUT"
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    TRANSIENT = "TRANSIENT"
    LIVE_NOT_AUTHORIZED = "LIVE_NOT_AUTHORIZED"
    CAPABILITY_DRIFT = "CAPABILITY_DRIFT"
    COST_LIMIT = "COST_LIMIT"


class ProviderTaskState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ProviderAttemptState(StrEnum):
    RESERVED = "RESERVED"
    SUBMITTED = "SUBMITTED"
    WATCHING = "WATCHING"
    DOWNLOADING = "DOWNLOADING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    HUMAN_GATE = "HUMAN_GATE"


class ProviderProfile(Contract):
    provider: str
    model: str
    aspect_ratio: str = "9:16"
    resolution: str = "1080p"
    min_duration_ms: int = 4000
    max_duration_ms: int = 15000
    max_in_flight: int = 2


class SnapshotStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    REVOKED = "REVOKED"


class PricingInputMode(StrEnum):
    WITHOUT_VIDEO = "WITHOUT_VIDEO"
    WITH_VIDEO = "WITH_VIDEO"


class ProviderCapabilitySnapshot(Contract):
    snapshot_revision: str
    status: SnapshotStatus
    provider: str
    model: str
    aspect_ratios: tuple[str, ...] = Field(min_length=1)
    resolutions: tuple[str, ...] = Field(min_length=1)
    fps: Annotated[int, Field(gt=0)]
    min_duration_ms: Annotated[int, Field(gt=0)]
    max_duration_ms: Annotated[int, Field(gt=0)]
    source_url: str
    source_updated_at: datetime
    captured_at: datetime
    valid_until: datetime
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderPricingSnapshot(Contract):
    snapshot_revision: str
    status: SnapshotStatus
    provider: str
    model: str
    resolution: str
    input_mode: PricingInputMode
    currency: Literal["CNY"] = "CNY"
    billing_unit: str
    unit_price_cny: Annotated[Decimal, Field(gt=0)]
    worst_case_units: Annotated[Decimal, Field(gt=0)]
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    source_url: str
    source_updated_at: datetime
    captured_at: datetime
    valid_until: datetime
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LiveAuthorization(Contract):
    authorization_id: str
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_cost_cny: Annotated[Decimal, Field(gt=0)]
    expires_at: datetime
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_posts: Literal[1] = 1


class CanaryPlan(Contract):
    state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    run_id: str
    job_id: str
    attempt: Literal[1] = 1
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    approved_cost_ceiling_cny: Annotated[Decimal, Field(gt=0)]
    planned_at: datetime
    posts_allowed: Literal[0] = 0


class InputMaterial(Contract):
    reference: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderRequest(Contract):
    run_id: str
    job_id: str
    attempt: Annotated[int, Field(ge=1, le=2)]
    provider: str
    model: str
    prompt: str
    duration_ms: Annotated[int, Field(gt=0)]
    aspect_ratio: str
    resolution: str
    input_materials: tuple[InputMaterial, ...] = ()
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProviderSubmission(Contract):
    provider_task_id: str
    state: ProviderTaskState


class ProviderFailure(Contract):
    failure_class: ProviderFailureClass
    code: str | None = None
    message: str
    retryable: bool = False


class ProviderTaskSnapshot(Contract):
    provider_task_id: str
    state: ProviderTaskState
    usage_tokens: int | None = None
    failure: ProviderFailure | None = None
    # Ephemeral signed URLs are adapter-only data and deliberately excluded.
    result_available: bool = False


class DownloadedArtifact(Contract):
    provider_task_id: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0)]
    ffprobe: dict[str, object]


class CancelResult(Contract):
    provider_task_id: str
    cancelled: bool


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
