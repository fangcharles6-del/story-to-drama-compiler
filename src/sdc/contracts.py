"""Versioned, immutable public contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Final, Literal
from unicodedata import normalize
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION: Final[Literal["1.0.0"]] = "1.0.0"
CANARY_PROVIDER: Final[Literal["volcengine_ark"]] = "volcengine_ark"
CANARY_MODEL: Final[Literal["doubao-seedance-2-0-260128"]] = "doubao-seedance-2-0-260128"
EVIDENCE_MAX_OBJECT_BYTES: Final = 64 * 1024 * 1024
EVIDENCE_MAX_BUNDLE_BYTES: Final = 512 * 1024 * 1024
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
    generate_audio: bool = False


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


class EvidenceBoundCanaryPlan(Contract):
    """Zero-authority plan whose snapshots came from one trusted FRESH bundle."""

    document_type: Literal["sdc.evidence-bound-canary-plan"] = "sdc.evidence-bound-canary-plan"
    evidence_profile: Literal["ark-canary-capability-pricing-v1"] = (
        "ark-canary-capability-pricing-v1"
    )
    evidence_bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_valid_until: datetime
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

    @model_validator(mode="after")
    def validate_evidence_window(self) -> EvidenceBoundCanaryPlan:
        for field, value in (
            ("planned_at", self.planned_at),
            ("evidence_valid_until", self.evidence_valid_until),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field} must include a timezone")
        if self.planned_at > self.evidence_valid_until:
            raise ValueError("planned_at must not exceed the evidence validity window")
        if self.worst_case_cost_cny > self.approved_cost_ceiling_cny:
            raise ValueError("worst-case cost must not exceed the approved ceiling")
        return self


class EvidenceBoundLiveAuthorization(Contract):
    """Inert one-POST authorization candidate bound to reviewed evidence and runtime policy."""

    document_type: Literal["sdc.evidence-bound-live-authorization"] = (
        "sdc.evidence-bound-live-authorization"
    )
    evidence_profile: Literal["ark-canary-capability-pricing-v1"] = (
        "ark-canary-capability-pricing-v1"
    )
    authorization_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    submission_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_release_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_valid_until: datetime
    entitlement_anchor_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    entitlement_valid_until: datetime
    provider_region: Literal["cn-beijing"] = "cn-beijing"
    task_queue: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    ledger_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )
    run_id: str = Field(min_length=1, max_length=256)
    job_id: str = Field(min_length=1, max_length=128)
    attempt: Literal[1] = 1
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    capability_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pricing_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    worst_case_cost_cny: Annotated[Decimal, Field(gt=0)]
    max_cost_cny: Annotated[Decimal, Field(gt=0, le=15)]
    authorized_at: datetime
    expires_at: datetime
    nonce: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_posts: Literal[1] = 1

    @field_validator(
        "evidence_valid_until",
        "entitlement_valid_until",
        "authorized_at",
        "expires_at",
    )
    @classmethod
    def canonicalize_authorization_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence-bound authorization datetimes must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_authorization_window(self) -> EvidenceBoundLiveAuthorization:
        if self.authorized_at >= self.expires_at:
            raise ValueError("authorization expiry must be later than authorized_at")
        if self.expires_at > min(self.evidence_valid_until, self.entitlement_valid_until):
            raise ValueError("authorization must expire within evidence and entitlement validity")
        if self.worst_case_cost_cny > self.max_cost_cny:
            raise ValueError("authorization max cost must cover the reviewed worst-case cost")
        if self.entitlement_anchor_sha256 in {
            self.evidence_bundle_id,
            self.evidence_logical_tree_sha256,
            self.capability_snapshot_sha256,
            self.pricing_snapshot_sha256,
        }:
            raise ValueError("entitlement must use an independent reviewed anchor")
        return self


class EvidenceAcquisition(StrEnum):
    FRESH = "FRESH"
    INHERITED = "INHERITED"
    LEGACY_IMPORT = "LEGACY_IMPORT"


_WINDOWS_RESERVED_PATH_STEMS = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
    | {f"com{index}" for index in "¹²³"}
    | {f"lpt{index}" for index in "¹²³"}
)
_EVIDENCE_SOURCE_HOSTS = frozenset(
    {"console.volcengine.com", "docs.volcengine.com", "www.volcengine.com"}
)


def _canonical_evidence_path(value: str) -> str:
    if not value or len(value) > 512:
        raise ValueError("evidence logical path must contain 1..512 characters")
    if normalize("NFC", value) != value:
        raise ValueError("evidence logical path must use NFC Unicode normalization")
    if (
        "\\" in value
        or any(character in '<>:"|?*' for character in value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError("evidence logical path contains a non-portable character")
    path = PurePosixPath(value)
    if not path.parts or value == "." or path.is_absolute() or path.as_posix() != value:
        raise ValueError("evidence logical path must be canonical and relative")
    for part in path.parts:
        if part in {"", ".", ".."} or len(part) > 255 or part.rstrip(" .") != part:
            raise ValueError("evidence logical path contains an unsafe segment")
        if part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_PATH_STEMS:
            raise ValueError("evidence logical path contains a reserved device name")
    return value


def _require_timezone(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")


class EvidenceObject(Contract):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: Annotated[int, Field(gt=0, le=EVIDENCE_MAX_OBJECT_BYTES)]
    media_type: str = Field(
        min_length=3,
        max_length=127,
        pattern=r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$",
    )

    @field_validator("media_type")
    @classmethod
    def validate_media_type(cls, value: str) -> str:
        if value != value.lower():
            raise ValueError("evidence media type must use canonical lowercase spelling")
        return value


class EvidenceMember(Contract):
    logical_path: str
    role: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9._-]*$")
    object_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_schema_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _canonical_evidence_path(value)


class EvidenceCapture(Contract):
    capture_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    kind: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9._-]*$")
    source_url: str | None = Field(default=None, max_length=2048)
    source_updated_at: datetime | None = None
    captured_at: datetime
    valid_until: datetime
    acquisition: EvidenceAcquisition
    origin_anchor_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    origin_valid_until: datetime | None = None
    member_paths: tuple[str, ...] = Field(min_length=1)

    @field_validator(
        "source_updated_at", "captured_at", "valid_until", "origin_valid_until"
    )
    @classmethod
    def canonicalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        _require_timezone(value, "evidence datetime")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_capture(self) -> EvidenceCapture:
        if self.source_updated_at is not None:
            if self.source_updated_at > self.captured_at:
                raise ValueError("source_updated_at must not be later than captured_at")
        if self.captured_at > self.valid_until:
            raise ValueError("captured_at must not be later than valid_until")
        if self.source_url is not None:
            parsed = urlparse(self.source_url)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError(
                    "source_url must be an approved Volcengine HTTPS URL"
                ) from exc
            safe_doc_query = (
                parsed.hostname in {"docs.volcengine.com", "www.volcengine.com"}
                and parsed.query in {"lang=zh", "lang=en"}
            )
            has_noncanonical_character = "\\" in self.source_url or any(
                ord(character) <= 32 or ord(character) == 127
                for character in self.source_url
            )
            if (
                has_noncanonical_character
                or parsed.scheme != "https"
                or parsed.hostname not in _EVIDENCE_SOURCE_HOSTS
                or parsed.netloc != parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or port is not None
                or (parsed.query and not safe_doc_query)
                or parsed.fragment
            ):
                raise ValueError("source_url must be an approved Volcengine HTTPS URL")
        canonical_paths = tuple(_canonical_evidence_path(path) for path in self.member_paths)
        if canonical_paths != tuple(sorted(set(canonical_paths))):
            raise ValueError("capture member_paths must be unique and sorted")
        if self.acquisition is EvidenceAcquisition.FRESH:
            if self.origin_anchor_sha256 is not None or self.origin_valid_until is not None:
                raise ValueError("fresh evidence must not name an origin")
        elif self.origin_anchor_sha256 is None or self.origin_valid_until is None:
            raise ValueError("inherited or legacy evidence must name its origin and expiry")
        elif self.valid_until > self.origin_valid_until:
            raise ValueError("inherited evidence must not extend its origin validity")
        return self


def evidence_logical_tree_sha256(
    objects: tuple[EvidenceObject, ...], members: tuple[EvidenceMember, ...]
) -> str:
    object_by_hash = {item.sha256: item for item in objects}
    resolved: list[dict[str, object]] = []
    for member in sorted(members, key=lambda item: item.logical_path):
        item = object_by_hash.get(member.object_sha256)
        if item is None:
            raise ValueError(f"member references undeclared object: {member.logical_path}")
        resolved.append(
            {
                "logical_path": member.logical_path,
                "role": member.role,
                "content_schema_version": member.content_schema_version,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "media_type": item.media_type,
            }
        )
    descriptor = json.dumps(
        resolved, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    return hashlib.sha256(b"sdc:evidence-logical-tree:1.0.0\0" + descriptor).hexdigest()


class EvidenceBundleContent(Contract):
    created_at: datetime
    valid_until: datetime
    predecessor_bundle_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    objects: tuple[EvidenceObject, ...] = Field(min_length=1)
    members: tuple[EvidenceMember, ...] = Field(min_length=1)
    captures: tuple[EvidenceCapture, ...] = Field(min_length=1)
    resolved_logical_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("created_at", "valid_until")
    @classmethod
    def canonicalize_datetime(cls, value: datetime) -> datetime:
        _require_timezone(value, "bundle datetime")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_bundle_content(self) -> EvidenceBundleContent:
        object_hashes = tuple(item.sha256 for item in self.objects)
        if object_hashes != tuple(sorted(set(object_hashes))):
            raise ValueError("evidence objects must be unique and sorted by sha256")

        member_paths = tuple(item.logical_path for item in self.members)
        if member_paths != tuple(sorted(set(member_paths))):
            raise ValueError("evidence members must be unique and sorted by logical_path")
        if len({path.casefold() for path in member_paths}) != len(member_paths):
            raise ValueError("evidence logical paths must remain unique when case-folded")

        declared_objects = set(object_hashes)
        referenced_objects = {item.object_sha256 for item in self.members}
        if referenced_objects != declared_objects:
            raise ValueError("evidence objects and member references must form an exact closure")
        if sum(item.size_bytes for item in self.objects) > EVIDENCE_MAX_BUNDLE_BYTES:
            raise ValueError("evidence bundle exceeds the total object byte limit")

        capture_ids = tuple(item.capture_id for item in self.captures)
        if capture_ids != tuple(sorted(set(capture_ids))):
            raise ValueError("evidence captures must be unique and sorted by capture_id")
        captured_paths = [path for capture in self.captures for path in capture.member_paths]
        if len(captured_paths) != len(set(captured_paths)) or set(captured_paths) != set(
            member_paths
        ):
            raise ValueError(
                "captures must reference every evidence member exactly once"
            )
        if self.created_at < max(capture.captured_at for capture in self.captures):
            raise ValueError("created_at must not precede an evidence capture")

        expected_valid_until = min(capture.valid_until for capture in self.captures)
        if self.valid_until != expected_valid_until:
            raise ValueError("bundle valid_until must equal the earliest capture expiry")
        expected_tree = evidence_logical_tree_sha256(self.objects, self.members)
        if self.resolved_logical_tree_sha256 != expected_tree:
            raise ValueError("resolved evidence tree digest does not match bundle members")
        return self


def evidence_bundle_content_sha256(content: EvidenceBundleContent) -> str:
    descriptor = json.dumps(
        content.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(b"sdc:evidence-bundle-content:1.0.0\0" + descriptor).hexdigest()


class EvidenceBundle(Contract):
    document_type: Literal["sdc.evidence-bundle"] = "sdc.evidence-bundle"
    bundle_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: EvidenceBundleContent

    @model_validator(mode="after")
    def validate_bundle_id(self) -> EvidenceBundle:
        if self.bundle_id != evidence_bundle_content_sha256(self.content):
            raise ValueError("bundle_id does not match canonical bundle content")
        if self.bundle_id == self.content.predecessor_bundle_id:
            raise ValueError("bundle predecessor must differ from the current bundle")
        return self


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
    generate_audio: bool
    input_materials: tuple[InputMaterial, ...] = ()
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def provider_request_fingerprint(request: ProviderRequest) -> str:
    """Hash every explicit Provider input while excluding the self-referential digest."""
    body = request.model_dump(exclude={"request_fingerprint"}, mode="json")
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class CanaryExecution(Contract):
    """Exact workflow payload for the separately authorized one-task canary route."""

    run_id: str = Field(min_length=1)
    graph: JobGraph
    request: ProviderRequest

    @model_validator(mode="after")
    def validate_exact_canary(self) -> CanaryExecution:
        if len(self.graph.jobs) != 1:
            raise ValueError("canary workflow must contain exactly one Job")
        job = self.graph.jobs[0]
        if job.depends_on:
            raise ValueError("canary Job must not depend on another Job")
        if self.request.run_id != self.run_id or self.request.job_id != job.id:
            raise ValueError("canary run_id/job_id must match the Workflow payload")
        if self.request.attempt != 1:
            raise ValueError("canary permits Attempt 1 only")
        if self.request.provider != CANARY_PROVIDER or self.request.model != CANARY_MODEL:
            raise ValueError("canary Provider and Seedance 2.0 model are fixed")
        if (
            self.request.duration_ms != 4000
            or self.request.aspect_ratio != "9:16"
            or self.request.resolution != "1080p"
        ):
            raise ValueError("canary output is fixed to 9:16, 1080p, and 4000 ms")
        if self.request.generate_audio:
            raise ValueError("canary generate_audio must be false")
        if self.request.input_materials:
            raise ValueError("canary is text-only and accepts no input materials")
        if not self.request.prompt.strip():
            raise ValueError("canary text prompt must not be empty")
        if self.request.prompt != job.prompt or self.request.duration_ms != job.duration_ms:
            raise ValueError("canary request must match the single compiled Job")
        if provider_request_fingerprint(self.request) != self.request.request_fingerprint:
            raise ValueError("canary request fingerprint does not match the Workflow request")
        return self


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
