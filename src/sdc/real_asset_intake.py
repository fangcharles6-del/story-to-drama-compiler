"""Offline, fail-closed intake for the Creative Sample Pilot's real media.

This module has no Provider, network, runtime, database, or authorization integration.  It
freezes explicitly mapped local bytes, records mechanical media checks, and requires two
independent reviews before deriving a new candidate CreativeSampleSpec.  Even a successful
derivation remains behind HUMAN_GATE and grants zero Provider requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, cast
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sdc.compiler import compile_creative_sample, stable_id
from sdc.contracts import (
    CharacterAssetVersion,
    CharacterBible,
    CreativeSampleCompilation,
    CreativeSampleSpec,
    SceneAssetVersion,
    SceneBible,
)
from sdc.creative_media import CreativeMediaError, validate_local_path
from sdc.creative_pilot import build_creative_sample_pilot_documents
from sdc.real_asset_media import (
    RealAssetMediaError,
    SafeLocalFile,
    inspect_bgm_wav,
    inspect_png,
    inspect_voice_wav,
)

INTAKE_PROFILE: Literal["creative-sample-real-asset-intake-v1"] = (
    "creative-sample-real-asset-intake-v1"
)
INTAKE_TEMPLATE_NAME = "intake-template.json"
INTAKE_GAP_NAME = "gap-report.json"
INTAKE_SUBMISSION_NAME = "intake-submission.json"
INTAKE_PACK_NAME = "asset-pack.json"
INTAKE_RIGHTS_NAME = "rights-manifest.json"
INTAKE_REVISION_NAME = "real-asset-revision.json"
INTAKE_REAL_SPEC_NAME = "creative-sample-spec.json"
INTAKE_JSON_LIMIT = 1024 * 1024
MAX_INTAKE_TOTAL_BYTES = 256 * 1024 * 1024

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_PORTABLE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_WINDOWS_RESERVED = frozenset(
    {
        "aux",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)


class RealAssetIntakeError(RuntimeError):
    """An offline real-asset intake gate failed closed."""


class _IntakeModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


def _canonical_payload(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_document(value: BaseModel) -> bytes:
    return (
        json.dumps(
            value.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _model_sha256(value: BaseModel) -> str:
    return _sha256(_canonical_payload(value))


def _portable_text(value: str, *, field: str, maximum: int = 1000) -> str:
    if not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1..{maximum} characters")
    if value != value.strip() or value != normalize("NFC", value):
        raise ValueError(f"{field} must be trimmed NFC text")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{field} must not contain control characters")
    return value


def _logical_path(value: str) -> str:
    if not value or len(value) > 256 or "\\" in value:
        raise ValueError("intake logical paths must be bounded portable relative paths")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError("intake logical paths must be canonical relative paths")
    for part in path.parts:
        if (
            part in {"", ".", ".."}
            or part.rstrip(" .") != part
            or normalize("NFC", part) != part
            or any(character in '<>:"|?*' for character in part)
            or any(ord(character) < 32 or ord(character) == 127 for character in part)
            or part.split(".", 1)[0].casefold() in _WINDOWS_RESERVED
        ):
            raise ValueError("intake logical paths contain a non-portable component")
    return value


def _utc_seconds(value: str, *, field: str) -> str:
    if not __import__("re").fullmatch(_UTC_SECONDS, value):
        raise ValueError(f"{field} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{field} must be canonical UTC seconds")
    return value


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


class RealAssetRequirement(_IntakeModel):
    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    kind: Literal["IMAGE", "VOICE", "BGM"]
    subject_kind: Literal["CHARACTER", "SCENE", "DIALOGUE", "SCORE"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    pilot_requirement_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    media_type: Literal["image/png", "audio/wav"]
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, gt=0)
    exact_text: str | None = Field(default=None, max_length=1000)
    forbidden_fixture_asset_id: str | None = Field(default=None, pattern=_PORTABLE_ID)
    forbidden_fixture_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    technical_profile: str = Field(pattern=_PORTABLE_ID)
    substitution_options: tuple[str, ...] = Field(min_length=1)

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("exact_text")
    @classmethod
    def validate_exact_text(cls, value: str | None) -> str | None:
        if value is not None:
            return _portable_text(value, field="exact dialogue", maximum=1000)
        return value

    @field_validator("substitution_options")
    @classmethod
    def validate_substitution_options(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("replacement guidance must be unique")
        return tuple(
            _portable_text(item, field="replacement guidance", maximum=1000) for item in value
        )

    @model_validator(mode="after")
    def validate_shape(self) -> RealAssetRequirement:
        expected = stable_id(
            "real_asset_requirement",
            {
                "kind": self.kind,
                "logical_path": self.logical_path,
                "pilot_requirement_id": self.pilot_requirement_id,
                "subject_id": self.subject_id,
            },
        )
        if self.requirement_id != expected:
            raise ValueError("real asset requirement ID must bind its exact Pilot role")
        if self.kind == "IMAGE":
            if (
                self.media_type != "image/png"
                or self.subject_kind not in {"CHARACTER", "SCENE"}
                or self.start_ms is not None
                or self.end_ms is not None
                or self.exact_text is not None
                or self.forbidden_fixture_asset_id is None
                or self.forbidden_fixture_sha256 is None
                or self.technical_profile != "strict-png-real-reference-v1"
            ):
                raise ValueError("image requirement does not match the strict PNG profile")
        elif self.kind == "VOICE":
            if (
                self.media_type != "audio/wav"
                or self.subject_kind != "DIALOGUE"
                or self.start_ms is None
                or self.end_ms is None
                or self.start_ms >= self.end_ms
                or self.exact_text is None
                or self.forbidden_fixture_asset_id is not None
                or self.forbidden_fixture_sha256 is not None
                or self.technical_profile != "pcm16-48khz-mono-dialogue-v1"
            ):
                raise ValueError("voice requirement does not match the exact dialogue profile")
        elif (
            self.media_type != "audio/wav"
            or self.subject_kind != "SCORE"
            or self.start_ms != 0
            or self.end_ms != 72000
            or self.exact_text is not None
            or self.forbidden_fixture_asset_id is not None
            or self.forbidden_fixture_sha256 is not None
            or self.technical_profile != "pcm16-48khz-stereo-score-72s-v1"
        ):
            raise ValueError("BGM requirement does not match the exact score profile")
        return self


class RealAssetSubmissionItem(_IntakeModel):
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    logical_path: str
    status: Literal["MISSING", "SUBMITTED"] = "MISSING"
    source_authority: (
        Literal["USER_PROVIDED_LOCAL", "SEPARATELY_APPROVED_LOCAL_GENERATION"] | None
    ) = None
    expected_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)
    expected_size_bytes: int | None = Field(default=None, gt=0)
    provenance_record_sha256: str | None = Field(default=None, pattern=_LOWER_SHA256)

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @model_validator(mode="after")
    def validate_submission_state(self) -> RealAssetSubmissionItem:
        bound = (
            self.source_authority,
            self.expected_sha256,
            self.expected_size_bytes,
            self.provenance_record_sha256,
        )
        if self.status == "MISSING" and any(item is not None for item in bound):
            raise ValueError("missing intake rows cannot claim source or byte identity")
        if self.status == "SUBMITTED" and any(item is None for item in bound):
            raise ValueError("submitted intake rows require exact source and byte identity")
        return self


class CreativeSampleRealAssetIntakeTemplate(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-intake-template"] = (
        "sdc.creative-sample-real-asset-intake-template"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    template_id: str = Field(pattern=r"^real_asset_intake_template_[0-9a-f]{20}$")
    pilot_pack_id: str = Field(pattern=r"^creative_pilot_pack_[0-9a-f]{20}$")
    pilot_sample_spec_sha256: str = Field(pattern=_LOWER_SHA256)
    pilot_compilation_id: str = Field(pattern=r"^creative_sample_[0-9a-f]{20}$")
    pilot_ordered_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    forbidden_fixture_asset_ids: tuple[str, ...] = Field(min_length=4, max_length=4)
    forbidden_fixture_sha256: tuple[str, ...] = Field(min_length=4, max_length=4)
    requirements: tuple[RealAssetRequirement, ...] = Field(min_length=14, max_length=14)
    status: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="after")
    def validate_template(self) -> CreativeSampleRealAssetIntakeTemplate:
        if self.template_id != stable_id(
            "real_asset_intake_template",
            self.model_dump(mode="json", exclude={"template_id"}),
        ):
            raise ValueError("intake template ID must bind its complete canonical content")
        if tuple(item.ordinal for item in self.requirements) != tuple(range(14)):
            raise ValueError("intake requirements must use exact canonical ordinals")
        if len({item.requirement_id for item in self.requirements}) != 14:
            raise ValueError("intake requirement IDs must be unique")
        if len({item.logical_path.casefold() for item in self.requirements}) != 14:
            raise ValueError("intake logical paths must be unique without case aliases")
        if tuple(item.kind for item in self.requirements) != (
            "IMAGE",
            "IMAGE",
            "IMAGE",
            "IMAGE",
            *("VOICE" for _ in range(9)),
            "BGM",
        ):
            raise ValueError("intake template must contain exactly four images, nine voices, BGM")
        image_rows = self.requirements[:4]
        if self.forbidden_fixture_asset_ids != tuple(
            sorted(
                item.forbidden_fixture_asset_id
                for item in image_rows
                if item.forbidden_fixture_asset_id
            )
        ):
            raise ValueError("fixture asset denylist must exactly cover Pilot active assets")
        if self.forbidden_fixture_sha256 != tuple(
            sorted(
                item.forbidden_fixture_sha256
                for item in image_rows
                if item.forbidden_fixture_sha256
            )
        ):
            raise ValueError("fixture digest denylist must exactly cover Pilot placeholders")
        return self


class CreativeSampleRealAssetSubmission(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-submission"] = (
        "sdc.creative-sample-real-asset-submission"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    submission_id: str = Field(pattern=r"^real_asset_submission_[0-9a-f]{20}$")
    template_id: str = Field(pattern=r"^real_asset_intake_template_[0-9a-f]{20}$")
    items: tuple[RealAssetSubmissionItem, ...] = Field(min_length=14, max_length=14)
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="after")
    def validate_submission(self) -> CreativeSampleRealAssetSubmission:
        if self.submission_id != stable_id(
            "real_asset_submission",
            self.model_dump(mode="json", exclude={"submission_id"}),
        ):
            raise ValueError("submission ID must bind its complete canonical content")
        return self


class RealAssetGapRow(_IntakeModel):
    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    logical_path: str
    disposition: Literal[
        "MISSING",
        "IDENTITY_MISMATCH",
        "TECHNICAL_REJECTED",
        "REVIEW_PENDING",
        "DISPUTED",
        "EXPIRED",
        "APPROVED",
    ]
    failures: tuple[str, ...] = Field(min_length=1)
    replacement_guidance: tuple[str, ...] = Field(min_length=1)

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("failures", "replacement_guidance")
    @classmethod
    def validate_texts(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("gap report messages must be unique")
        return tuple(_portable_text(item, field="gap report message") for item in value)


class CreativeSampleRealAssetGapReport(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-gap-report"] = (
        "sdc.creative-sample-real-asset-gap-report"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    report_id: str = Field(pattern=r"^real_asset_gap_report_[0-9a-f]{20}$")
    template_id: str = Field(pattern=r"^real_asset_intake_template_[0-9a-f]{20}$")
    submission_id: str | None = Field(default=None, pattern=r"^real_asset_submission_[0-9a-f]{20}$")
    rows: tuple[RealAssetGapRow, ...] = Field(min_length=14, max_length=14)
    missing_count: Annotated[int, Field(ge=0, le=14)]
    rejected_count: Annotated[int, Field(ge=0, le=14)]
    pending_count: Annotated[int, Field(ge=0, le=14)]
    approved_count: Annotated[int, Field(ge=0, le=14)]
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    ready_for_rights_review: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="after")
    def validate_report(self) -> CreativeSampleRealAssetGapReport:
        if tuple(item.ordinal for item in self.rows) != tuple(range(14)):
            raise ValueError("gap report must preserve all fourteen canonical rows")
        if len({item.requirement_id for item in self.rows}) != 14:
            raise ValueError("gap report requirement IDs must be unique")
        dispositions = tuple(item.disposition for item in self.rows)
        expected = {
            "missing_count": dispositions.count("MISSING"),
            "rejected_count": sum(
                item in {"IDENTITY_MISMATCH", "TECHNICAL_REJECTED", "DISPUTED", "EXPIRED"}
                for item in dispositions
            ),
            "pending_count": dispositions.count("REVIEW_PENDING"),
            "approved_count": dispositions.count("APPROVED"),
        }
        for field, count in expected.items():
            if getattr(self, field) != count:
                raise ValueError("gap report summary does not match its exact rows")
        if self.report_id != stable_id(
            "real_asset_gap_report",
            self.model_dump(mode="json", exclude={"report_id"}),
        ):
            raise ValueError("gap report ID must bind its complete canonical content")
        return self


def _build_requirements() -> tuple[RealAssetRequirement, ...]:
    spec, pilot = build_creative_sample_pilot_documents()
    asset_by_path = {item.intended_logical_path: item for item in pilot.asset_requirements}
    audio_by_path = {item.intended_logical_path: item for item in pilot.audio_requirements}
    requested_paths = (
        "assets/characters/gu-yan/v1.png",
        "assets/characters/su-qing/v1.png",
        "assets/scenes/office-night/v1.png",
        "assets/scenes/rooftop-dawn/v1.png",
        *(f"audio/voices/{ordinal:02d}.wav" for ordinal in range(9)),
        "audio/bgm/background.wav",
    )
    line_by_id = {item.line_id: item for item in spec.dialogue}
    requirements: list[RealAssetRequirement] = []
    for ordinal, logical_path in enumerate(requested_paths):
        if ordinal < 4:
            source = asset_by_path[logical_path]
            requirement_payload = {
                "kind": "IMAGE",
                "logical_path": logical_path,
                "pilot_requirement_id": source.requirement_id,
                "subject_id": source.subject_id,
            }
            requirements.append(
                RealAssetRequirement(
                    ordinal=ordinal,
                    requirement_id=stable_id("real_asset_requirement", requirement_payload),
                    kind="IMAGE",
                    subject_kind=source.subject_kind,
                    subject_id=source.subject_id,
                    pilot_requirement_id=source.requirement_id,
                    logical_path=logical_path,
                    media_type="image/png",
                    forbidden_fixture_asset_id=source.asset_version_id,
                    forbidden_fixture_sha256=source.placeholder_sha256,
                    technical_profile="strict-png-real-reference-v1",
                    substitution_options=(
                        "仅可由用户明确提供的同角色或同场景本地PNG替换。",
                        "也可使用在另一任务中单独批准生成、随后本地交付的同角色或同场景PNG。",
                        "任何编辑、转换或重新导出均是新字节，必须建立新来源记录和双人复核。",
                    ),
                )
            )
            continue
        audio_source = audio_by_path[logical_path]
        kind: Literal["VOICE", "BGM"] = audio_source.kind
        line = line_by_id.get(audio_source.line_id) if audio_source.line_id is not None else None
        subject_id = (
            audio_source.line_id
            if audio_source.line_id is not None
            else audio_source.requirement_id
        )
        requirement_payload = {
            "kind": kind,
            "logical_path": logical_path,
            "pilot_requirement_id": audio_source.requirement_id,
            "subject_id": subject_id,
        }
        requirements.append(
            RealAssetRequirement(
                ordinal=ordinal,
                requirement_id=stable_id("real_asset_requirement", requirement_payload),
                kind=kind,
                subject_kind="DIALOGUE" if kind == "VOICE" else "SCORE",
                subject_id=subject_id,
                pilot_requirement_id=audio_source.requirement_id,
                logical_path=logical_path,
                media_type="audio/wav",
                start_ms=audio_source.start_ms,
                end_ms=audio_source.end_ms,
                exact_text=line.text if line is not None else None,
                technical_profile=(
                    "pcm16-48khz-mono-dialogue-v1"
                    if kind == "VOICE"
                    else "pcm16-48khz-stereo-score-72s-v1"
                ),
                substitution_options=(
                    (
                        "仅可由用户明确提供的同说话角色、精确台词和时段本地WAV替换。"
                        if kind == "VOICE"
                        else "仅可由用户明确提供的无歌词72秒本地BGM WAV替换。"
                    ),
                    "也可使用在另一任务中单独批准生成、随后本地交付的同角色或同用途WAV。",
                    "任何剪辑、降噪、重采样或响度处理均是新字节，必须重新技术检查和双人复核。",
                ),
            )
        )
    return tuple(requirements)


def build_real_asset_intake_template() -> CreativeSampleRealAssetIntakeTemplate:
    """Build the deterministic, zero-authority fourteen-slot intake template."""
    spec, pilot = build_creative_sample_pilot_documents()
    requirements = _build_requirements()
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-intake-template",
        "profile": INTAKE_PROFILE,
        "pilot_pack_id": pilot.pack_id,
        "pilot_sample_spec_sha256": _model_sha256(spec),
        "pilot_compilation_id": pilot.compilation_id,
        "pilot_ordered_shot_ids": pilot.ordered_shot_ids,
        "forbidden_fixture_asset_ids": tuple(sorted(pilot.active_asset_version_ids)),
        "forbidden_fixture_sha256": tuple(
            sorted(item.placeholder_sha256 for item in pilot.asset_requirements)
        ),
        "requirements": tuple(item.model_dump(mode="json") for item in requirements),
        "status": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetIntakeTemplate(
        template_id=stable_id("real_asset_intake_template", canonical),
        pilot_pack_id=pilot.pack_id,
        pilot_sample_spec_sha256=_model_sha256(spec),
        pilot_compilation_id=pilot.compilation_id,
        pilot_ordered_shot_ids=pilot.ordered_shot_ids,
        forbidden_fixture_asset_ids=tuple(sorted(pilot.active_asset_version_ids)),
        forbidden_fixture_sha256=tuple(
            sorted(item.placeholder_sha256 for item in pilot.asset_requirements)
        ),
        requirements=requirements,
    )


def build_missing_real_asset_submission(
    template: CreativeSampleRealAssetIntakeTemplate | None = None,
) -> CreativeSampleRealAssetSubmission:
    """Build an explicit all-missing submission; no file is discovered or inferred."""
    selected = template or build_real_asset_intake_template()
    items = tuple(
        RealAssetSubmissionItem(
            requirement_id=item.requirement_id,
            logical_path=item.logical_path,
        )
        for item in selected.requirements
    )
    return build_real_asset_submission(items, template=selected)


def build_real_asset_submission(
    items: tuple[RealAssetSubmissionItem, ...],
    *,
    template: CreativeSampleRealAssetIntakeTemplate | None = None,
) -> CreativeSampleRealAssetSubmission:
    """Bind an operator-supplied exact fourteen-row mapping without inspecting its files."""
    selected = template or build_real_asset_intake_template()
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-submission",
        "profile": INTAKE_PROFILE,
        "template_id": selected.template_id,
        "items": tuple(item.model_dump(mode="json") for item in items),
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    submission = CreativeSampleRealAssetSubmission(
        submission_id=stable_id("real_asset_submission", canonical),
        template_id=selected.template_id,
        items=items,
    )
    _validate_submission_closure(selected, submission)
    return submission


def _validate_submission_closure(
    template: CreativeSampleRealAssetIntakeTemplate,
    submission: CreativeSampleRealAssetSubmission,
) -> None:
    if template != build_real_asset_intake_template():
        raise RealAssetIntakeError("intake template differs from the frozen Pilot binding")
    if submission.template_id != template.template_id:
        raise RealAssetIntakeError("submission does not bind the exact intake template")
    expected = tuple((item.requirement_id, item.logical_path) for item in template.requirements)
    actual = tuple((item.requirement_id, item.logical_path) for item in submission.items)
    if actual != expected:
        raise RealAssetIntakeError(
            "submission must preserve the exact ordered fourteen-slot closure"
        )


def build_real_asset_gap_report(
    submission: CreativeSampleRealAssetSubmission | None = None,
    template: CreativeSampleRealAssetIntakeTemplate | None = None,
) -> CreativeSampleRealAssetGapReport:
    """Report every unresolved row without inspecting or discovering a local file."""
    selected = template or build_real_asset_intake_template()
    current = submission or build_missing_real_asset_submission(selected)
    _validate_submission_closure(selected, current)
    rows: list[RealAssetGapRow] = []
    for requirement, item in zip(selected.requirements, current.items, strict=True):
        if item.status == "MISSING":
            disposition: Literal["MISSING", "REVIEW_PENDING"] = "MISSING"
            failures = ("本地素材尚未由用户显式提交，不能推断、搜索或自动批准。",)
        else:
            disposition = "REVIEW_PENDING"
            failures = ("精确字节尚未完成技术检查、不可变冻结和双人权利复核。",)
        rows.append(
            RealAssetGapRow(
                ordinal=requirement.ordinal,
                requirement_id=requirement.requirement_id,
                logical_path=requirement.logical_path,
                disposition=disposition,
                failures=failures,
                replacement_guidance=requirement.substitution_options,
            )
        )
    missing_count = sum(item.disposition == "MISSING" for item in rows)
    pending_count = sum(item.disposition == "REVIEW_PENDING" for item in rows)
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-gap-report",
        "profile": INTAKE_PROFILE,
        "template_id": selected.template_id,
        "submission_id": current.submission_id if submission is not None else None,
        "rows": tuple(item.model_dump(mode="json") for item in rows),
        "missing_count": missing_count,
        "rejected_count": 0,
        "pending_count": pending_count,
        "approved_count": 0,
        "current_gate": "HUMAN_GATE",
        "ready_for_rights_review": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetGapReport(
        report_id=stable_id("real_asset_gap_report", canonical),
        template_id=selected.template_id,
        submission_id=current.submission_id if submission is not None else None,
        rows=tuple(rows),
        missing_count=missing_count,
        rejected_count=0,
        pending_count=pending_count,
        approved_count=0,
    )


def _reject_json_constant(value: str) -> None:
    raise RealAssetIntakeError(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetIntakeError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _read_strict_json(path: Path, model: type[BaseModel]) -> BaseModel:
    try:
        absolute = validate_local_path(path, must_exist=True)
        info = absolute.lstat()
    except (CreativeMediaError, OSError) as exc:
        raise RealAssetIntakeError("intake JSON path is not a safe local regular file") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RealAssetIntakeError("intake JSON must be a non-linked regular file")
    if info.st_size > INTAKE_JSON_LIMIT:
        raise RealAssetIntakeError("intake JSON exceeds the 1 MiB boundary")
    try:
        with absolute.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            raw = handle.read(INTAKE_JSON_LIMIT + 1)
        after = absolute.lstat()
    except OSError as exc:
        raise RealAssetIntakeError("intake JSON could not be read") from exc
    if len(raw) > INTAKE_JSON_LIMIT:
        raise RealAssetIntakeError("intake JSON exceeds the 1 MiB boundary")

    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    after_attributes = int(getattr(after, "st_file_attributes", 0))
    if (
        identity(info) != identity(opened)
        or identity(opened) != identity(after)
        or len(raw) != opened.st_size
        or not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or not stat.S_ISREG(after.st_mode)
        or stat.S_ISLNK(after.st_mode)
        or bool(after_attributes & 0x400)
        or after.st_nlink != 1
    ):
        raise RealAssetIntakeError("intake JSON changed while it was read")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RealAssetIntakeError("intake JSON must not contain a UTF-8 BOM")
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RealAssetIntakeError("intake JSON is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise RealAssetIntakeError("intake JSON must contain one object")
    try:
        parsed = model.model_validate_json(raw, strict=True)
    except ValueError as exc:
        raise RealAssetIntakeError("intake JSON does not match its strict contract") from exc
    if raw != _canonical_document(parsed):
        raise RealAssetIntakeError("intake JSON bytes are not canonical sorted UTF-8")
    return parsed


def load_real_asset_intake_template(path: Path) -> CreativeSampleRealAssetIntakeTemplate:
    parsed = cast(
        CreativeSampleRealAssetIntakeTemplate,
        _read_strict_json(path, CreativeSampleRealAssetIntakeTemplate),
    )
    if parsed != build_real_asset_intake_template():
        raise RealAssetIntakeError("intake template does not match the frozen Pilot Pack")
    return parsed


def load_real_asset_submission(path: Path) -> CreativeSampleRealAssetSubmission:
    parsed = cast(
        CreativeSampleRealAssetSubmission,
        _read_strict_json(path, CreativeSampleRealAssetSubmission),
    )
    _validate_submission_closure(build_real_asset_intake_template(), parsed)
    return parsed


def _write_new_document(path: Path, value: BaseModel) -> None:
    try:
        target = validate_local_path(path, must_exist=False)
        validate_local_path(target.parent, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if os.path.lexists(target):
        raise RealAssetIntakeError("intake document output must be a new local file")
    try:
        with target.open("xb") as handle:
            handle.write(_canonical_document(value))
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise RealAssetIntakeError("intake document could not be published") from exc


def write_real_asset_intake_templates(root: Path) -> tuple[Path, Path]:
    """Publish only the non-private all-missing template and gap report."""
    template = build_real_asset_intake_template()
    gap = build_real_asset_gap_report(template=template)
    try:
        absolute = validate_local_path(root, must_exist=False)
        parent = validate_local_path(absolute.parent, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if os.path.lexists(absolute):
        raise RealAssetIntakeError("intake template output must be a new directory")
    stage = Path(tempfile.mkdtemp(prefix=f".{absolute.name}-", dir=parent))
    try:
        _write_new_document(stage / INTAKE_TEMPLATE_NAME, template)
        _write_new_document(stage / INTAKE_GAP_NAME, gap)
        os.replace(stage, absolute)
    except Exception:
        for name in (INTAKE_TEMPLATE_NAME, INTAKE_GAP_NAME):
            try:
                (stage / name).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            stage.rmdir()
        except OSError:
            pass
        raise
    return absolute / INTAKE_TEMPLATE_NAME, absolute / INTAKE_GAP_NAME


class RealImageTechnicalRecord(_IntakeModel):
    width: Annotated[int, Field(ge=512, le=4096)]
    height: Annotated[int, Field(ge=512, le=4096)]
    color_space: Literal["RGB", "RGBA_OPAQUE"]
    bit_depth: Literal[8] = 8
    interlaced: Literal[False] = False
    metadata_free: Literal[True] = True
    active_content_absent: Literal[True] = True
    distinct_color_count: Annotated[int, Field(ge=16)]
    semantic_privacy_reviewed: Literal[False] = False


class RealAudioTechnicalRecord(_IntakeModel):
    codec: Literal["pcm_s16le"] = "pcm_s16le"
    sample_rate_hz: Literal[48000] = 48000
    channels: Literal[1, 2]
    duration_ms: Annotated[int, Field(gt=0)]
    sample_count: Annotated[int, Field(gt=0)]
    rms_millidbfs: Annotated[int, Field(ge=-40000, le=-6000)]
    sample_peak_millidbfs: Annotated[int, Field(ge=-30000, le=-100)]
    clipped_sample_count: Literal[0] = 0
    silence_ppm: Annotated[int, Field(ge=0, le=800000)]
    semantic_content_reviewed: Literal[False] = False


class FrozenRealAssetDescriptor(_IntakeModel):
    ordinal: Annotated[int, Field(ge=0, le=13)]
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    kind: Literal["IMAGE", "VOICE", "BGM"]
    subject_id: str = Field(pattern=_PORTABLE_ID)
    logical_path: str
    object_path: str
    media_type: Literal["image/png", "audio/wav"]
    sha256: str = Field(pattern=_LOWER_SHA256)
    size_bytes: Annotated[int, Field(gt=0)]
    duration_ms: Annotated[int, Field(ge=0)]
    source_authority: Literal["USER_PROVIDED_LOCAL", "SEPARATELY_APPROVED_LOCAL_GENERATION"]
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    technical_profile: str = Field(pattern=_PORTABLE_ID)
    technical_record_sha256: str = Field(pattern=_LOWER_SHA256)
    image: RealImageTechnicalRecord | None = None
    audio: RealAudioTechnicalRecord | None = None

    @field_validator("logical_path", "object_path")
    @classmethod
    def validate_logical_paths(cls, value: str) -> str:
        return _logical_path(value)

    @model_validator(mode="after")
    def validate_descriptor(self) -> FrozenRealAssetDescriptor:
        if self.object_path != f"objects/{self.sha256[:2]}/{self.sha256}":
            raise ValueError("frozen object path must derive from its exact SHA-256")
        if (self.kind == "IMAGE") != (self.image is not None) or (self.kind == "IMAGE") == (
            self.audio is not None
        ):
            raise ValueError("frozen descriptor must contain exactly its applicable evidence")
        if (self.kind == "IMAGE" and self.duration_ms != 0) or (
            self.kind != "IMAGE"
            and (self.audio is None or self.duration_ms != self.audio.duration_ms)
        ):
            raise ValueError("frozen descriptor duration must match its exact media kind")
        evidence = self.image if self.image is not None else self.audio
        expected = _sha256(
            b"sdc:real-asset-technical-record:v1\0"
            + _canonical_payload(
                {
                    "kind": self.kind,
                    "media_sha256": self.sha256,
                    "media_size_bytes": self.size_bytes,
                    "profile": self.technical_profile,
                    "evidence": evidence.model_dump(mode="json") if evidence else None,
                }
            )
        )
        if self.technical_record_sha256 != expected:
            raise ValueError("technical record digest must bind media, profile and evidence")
        return self


class CreativeSampleFrozenRealAssetPackManifest(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-frozen-real-asset-pack"] = (
        "sdc.creative-sample-frozen-real-asset-pack"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    template_id: str = Field(pattern=r"^real_asset_intake_template_[0-9a-f]{20}$")
    submission_id: str = Field(pattern=r"^real_asset_submission_[0-9a-f]{20}$")
    pilot_pack_id: str = Field(pattern=r"^creative_pilot_pack_[0-9a-f]{20}$")
    objects: tuple[FrozenRealAssetDescriptor, ...] = Field(min_length=14, max_length=14)
    total_size_bytes: Annotated[int, Field(gt=0, le=MAX_INTAKE_TOTAL_BYTES)]
    state: Literal["FROZEN_UNREVIEWED"] = "FROZEN_UNREVIEWED"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    eligible_for_real_generation: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="after")
    def validate_pack(self) -> CreativeSampleFrozenRealAssetPackManifest:
        if tuple(item.ordinal for item in self.objects) != tuple(range(14)):
            raise ValueError("frozen pack objects must preserve all fourteen canonical ordinals")
        if len({item.requirement_id for item in self.objects}) != 14:
            raise ValueError("frozen pack requirements must be unique")
        if len({item.logical_path.casefold() for item in self.objects}) != 14:
            raise ValueError("frozen pack logical paths must be unique")
        if len({item.sha256 for item in self.objects}) != 14:
            raise ValueError("one byte object cannot silently satisfy multiple intake roles")
        if self.total_size_bytes != sum(item.size_bytes for item in self.objects):
            raise ValueError("frozen pack total size must match all exact objects")
        expected = stable_id(
            "real_asset_pack",
            self.model_dump(mode="json", exclude={"pack_id"}),
        )
        if self.pack_id != expected:
            raise ValueError("real asset pack ID must bind its complete canonical content")
        return self


class RealAssetRightsReview(_IntakeModel):
    ordinal: Annotated[int, Field(ge=0, le=27)]
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    requirement_id: str = Field(pattern=r"^real_asset_requirement_[0-9a-f]{20}$")
    logical_path: str
    reviewer_role: Literal["REVIEWER_A", "REVIEWER_B"]
    reviewer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    review_record_sha256: str = Field(pattern=_LOWER_SHA256)
    media_sha256: str = Field(pattern=_LOWER_SHA256)
    media_size_bytes: Annotated[int, Field(gt=0)]
    provenance_record_sha256: str = Field(pattern=_LOWER_SHA256)
    technical_record_sha256: str = Field(pattern=_LOWER_SHA256)
    source_authority: Literal["USER_PROVIDED_LOCAL", "SEPARATELY_APPROVED_LOCAL_GENERATION"]
    copyright_basis: str = Field(min_length=1, max_length=1000)
    likeness_basis: str = Field(min_length=1, max_length=1000)
    privacy_basis: str = Field(min_length=1, max_length=1000)
    territory: str = Field(min_length=1, max_length=256)
    use_scope: str = Field(min_length=1, max_length=1000)
    reviewed_at: str
    valid_until: str
    provenance_approved: bool
    copyright_approved: bool
    likeness_approved: bool
    privacy_approved: bool
    territory_approved: bool
    use_scope_approved: bool
    content_role_approved: bool
    decision: Literal["APPROVED", "REJECTED"]

    @field_validator("logical_path")
    @classmethod
    def validate_logical_path(cls, value: str) -> str:
        return _logical_path(value)

    @field_validator("copyright_basis", "likeness_basis", "privacy_basis", "territory", "use_scope")
    @classmethod
    def validate_rights_text(cls, value: str) -> str:
        return _portable_text(value, field="rights declaration")

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at(cls, value: str) -> str:
        return _utc_seconds(value, field="reviewed_at")

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="valid_until")

    @model_validator(mode="after")
    def validate_review(self) -> RealAssetRightsReview:
        outcomes = (
            self.provenance_approved,
            self.copyright_approved,
            self.likeness_approved,
            self.privacy_approved,
            self.territory_approved,
            self.use_scope_approved,
            self.content_role_approved,
        )
        if self.decision == "APPROVED" and not all(outcomes):
            raise ValueError("an approved review requires every declared rights gate to pass")
        if self.decision == "REJECTED" and all(outcomes):
            raise ValueError("a rejected review must identify at least one failed gate")
        if self.valid_until != "PERPETUAL" and _parse_utc(self.reviewed_at) >= _parse_utc(
            self.valid_until
        ):
            raise ValueError("rights validity must end strictly after its review time")
        return self


class CreativeSampleRealAssetRightsManifest(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-rights-manifest"] = (
        "sdc.creative-sample-real-asset-rights-manifest"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    manifest_id: str = Field(pattern=r"^real_asset_rights_[0-9a-f]{20}$")
    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    reviews: tuple[RealAssetRightsReview, ...] = Field(min_length=28, max_length=28)
    status: Literal["REVIEW_CANDIDATE"] = "REVIEW_CANDIDATE"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @model_validator(mode="after")
    def validate_manifest(self) -> CreativeSampleRealAssetRightsManifest:
        if tuple(item.ordinal for item in self.reviews) != tuple(range(28)):
            raise ValueError("rights manifest must use exact canonical review ordinals")
        roles = tuple(item.reviewer_role for item in self.reviews)
        if roles != tuple(role for _ in range(14) for role in ("REVIEWER_A", "REVIEWER_B")):
            raise ValueError("rights manifest must contain A then B for every exact object")
        if len({item.review_record_sha256 for item in self.reviews}) != 28:
            raise ValueError("all twenty-eight private review records must have unique digests")
        expected = stable_id(
            "real_asset_rights",
            self.model_dump(mode="json", exclude={"manifest_id"}),
        )
        if self.manifest_id != expected:
            raise ValueError("rights manifest ID must bind its complete canonical content")
        return self


class CreativeSampleRealAssetSpecDocument(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-spec"] = (
        "sdc.creative-sample-real-asset-spec"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    source_mode: Literal["IMPORTED_MEDIA"] = "IMPORTED_MEDIA"
    asset_pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    rights_manifest_id: str = Field(pattern=r"^real_asset_rights_[0-9a-f]{20}$")
    approval_scope: Literal["PASS_ASSET_INTAKE_ONLY"] = "PASS_ASSET_INTAKE_ONLY"
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0
    spec: CreativeSampleSpec


class CreativeSampleRealAssetRevision(_IntakeModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    document_type: Literal["sdc.creative-sample-real-asset-revision"] = (
        "sdc.creative-sample-real-asset-revision"
    )
    profile: Literal["creative-sample-real-asset-intake-v1"] = INTAKE_PROFILE
    revision_id: str = Field(pattern=r"^real_asset_revision_[0-9a-f]{20}$")
    revision_number: Literal[2] = 2
    predecessor_pilot_pack_id: str = Field(pattern=r"^creative_pilot_pack_[0-9a-f]{20}$")
    predecessor_spec_sha256: str = Field(pattern=_LOWER_SHA256)
    predecessor_compilation_id: str = Field(pattern=r"^creative_sample_[0-9a-f]{20}$")
    predecessor_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    asset_pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    rights_manifest_id: str = Field(pattern=r"^real_asset_rights_[0-9a-f]{20}$")
    evaluated_at: str
    real_spec_sha256: str = Field(pattern=_LOWER_SHA256)
    real_spec_document_sha256: str = Field(pattern=_LOWER_SHA256)
    real_spec: CreativeSampleSpec
    compilation: CreativeSampleCompilation
    ordered_shot_ids: tuple[str, ...] = Field(min_length=10, max_length=10)
    audio_bindings: tuple[FrozenRealAssetDescriptor, ...] = Field(min_length=10, max_length=10)
    decision: Literal["PASS_ASSET_INTAKE_ONLY"] = "PASS_ASSET_INTAKE_ONLY"
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_separate_provider_approval: Literal[True] = True
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("evaluated_at")
    @classmethod
    def validate_evaluated_at(cls, value: str) -> str:
        return _utc_seconds(value, field="evaluated_at")

    @model_validator(mode="after")
    def validate_revision(self) -> CreativeSampleRealAssetRevision:
        if self.real_spec_sha256 != _model_sha256(self.real_spec):
            raise ValueError("real revision must bind the exact rebuilt specification")
        spec_document = CreativeSampleRealAssetSpecDocument(
            asset_pack_id=self.asset_pack_id,
            rights_manifest_id=self.rights_manifest_id,
            spec=self.real_spec,
        )
        if self.real_spec_document_sha256 != _sha256(_canonical_document(spec_document)):
            raise ValueError("real revision must bind the exact portable specification document")
        rebuilt = compile_creative_sample(self.real_spec)
        if self.compilation != rebuilt:
            raise ValueError("real revision compilation must be an exact pure rebuild")
        if self.ordered_shot_ids != tuple(item.id for item in rebuilt.pir.shots):
            raise ValueError("real revision shot IDs must match the exact compilation")
        if tuple(item.kind for item in self.audio_bindings) != (
            *("VOICE" for _ in range(9)),
            "BGM",
        ):
            raise ValueError("real revision must bind the exact nine voices and BGM")
        expected = stable_id(
            "real_asset_revision",
            self.model_dump(mode="json", exclude={"revision_id"}),
        )
        if self.revision_id != expected:
            raise ValueError("real revision ID must bind its complete canonical content")
        return self


@dataclass(frozen=True, slots=True)
class FrozenRealAssetPack:
    root: Path
    manifest_path: Path
    manifest: CreativeSampleFrozenRealAssetPackManifest
    created: bool


@dataclass(frozen=True, slots=True)
class QualifiedRealAssetRevision:
    root: Path
    revision_path: Path
    revision: CreativeSampleRealAssetRevision
    created: bool


def _entry_is_link_like(path: Path, info: os.stat_result) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return (
        stat.S_ISLNK(info.st_mode)
        or bool(getattr(info, "st_file_attributes", 0) & 0x400)
        or bool(is_junction is not None and is_junction())
    )


def _scan_exact_tree(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    stack: list[tuple[Path, PurePosixPath]] = [(root, PurePosixPath())]
    while stack:
        current, relative = stack.pop()
        try:
            entries = tuple(os.scandir(current))
        except OSError as exc:
            raise RealAssetIntakeError("intake directory could not be enumerated") from exc
        for entry in entries:
            path = Path(entry.path)
            try:
                info = path.lstat()
            except OSError as exc:
                raise RealAssetIntakeError("intake directory entry could not be inspected") from exc
            if _entry_is_link_like(path, info):
                raise RealAssetIntakeError("intake directory closure must not contain links")
            logical = (relative / entry.name).as_posix()
            try:
                _logical_path(logical)
            except ValueError as exc:
                raise RealAssetIntakeError("intake tree contains a non-portable path") from exc
            if stat.S_ISDIR(info.st_mode):
                directories.add(logical)
                stack.append((path, relative / entry.name))
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise RealAssetIntakeError("intake tree must not contain hard-linked files")
                files.add(logical)
            else:
                raise RealAssetIntakeError("intake tree contains a non-regular filesystem object")
    return frozenset(files), frozenset(directories)


def _expected_directories(paths: tuple[str, ...]) -> frozenset[str]:
    result: set[str] = set()
    for item in paths:
        parent = PurePosixPath(item).parent
        while parent != PurePosixPath("."):
            result.add(parent.as_posix())
            parent = parent.parent
    return frozenset(result)


def _technical_digest(
    *,
    kind: str,
    source: SafeLocalFile,
    profile: str,
    evidence: RealImageTechnicalRecord | RealAudioTechnicalRecord,
) -> str:
    return _sha256(
        b"sdc:real-asset-technical-record:v1\0"
        + _canonical_payload(
            {
                "kind": kind,
                "media_sha256": source.sha256,
                "media_size_bytes": source.size_bytes,
                "profile": profile,
                "evidence": evidence.model_dump(mode="json"),
            }
        )
    )


def _inspect_submitted_item(
    *,
    requirement: RealAssetRequirement,
    item: RealAssetSubmissionItem,
    source_root: Path,
    template: CreativeSampleRealAssetIntakeTemplate,
) -> tuple[SafeLocalFile, FrozenRealAssetDescriptor]:
    path = source_root.joinpath(*PurePosixPath(requirement.logical_path).parts)
    try:
        if requirement.kind == "IMAGE":
            source, raw_evidence = inspect_png(
                path,
                forbidden_sha256=template.forbidden_fixture_sha256,
            )
            image = RealImageTechnicalRecord(**asdict(raw_evidence))
            audio = None
            evidence: RealImageTechnicalRecord | RealAudioTechnicalRecord = image
        elif requirement.kind == "VOICE":
            assert requirement.start_ms is not None and requirement.end_ms is not None
            source, raw_audio = inspect_voice_wav(
                path,
                maximum_duration_ms=requirement.end_ms - requirement.start_ms,
            )
            audio = RealAudioTechnicalRecord(**asdict(raw_audio))
            image = None
            evidence = audio
        else:
            source, raw_audio = inspect_bgm_wav(path)
            audio = RealAudioTechnicalRecord(**asdict(raw_audio))
            image = None
            evidence = audio
    except (RealAssetMediaError, ValueError) as exc:
        raise RealAssetIntakeError(
            f"technical media gate failed for requirement {requirement.requirement_id}"
        ) from exc
    if (
        item.status != "SUBMITTED"
        or item.source_authority is None
        or item.expected_sha256 is None
        or item.expected_size_bytes is None
        or item.provenance_record_sha256 is None
    ):
        raise RealAssetIntakeError("all fourteen exact intake rows must be explicitly submitted")
    if source.sha256 != item.expected_sha256 or source.size_bytes != item.expected_size_bytes:
        raise RealAssetIntakeError("submitted media identity differs from its explicit declaration")
    if source.sha256 in template.forbidden_fixture_sha256:
        raise RealAssetIntakeError("Pilot placeholder bytes cannot be admitted as real media")
    technical_record_sha256 = _technical_digest(
        kind=requirement.kind,
        source=source,
        profile=requirement.technical_profile,
        evidence=evidence,
    )
    descriptor = FrozenRealAssetDescriptor(
        ordinal=requirement.ordinal,
        requirement_id=requirement.requirement_id,
        kind=requirement.kind,
        subject_id=requirement.subject_id,
        logical_path=requirement.logical_path,
        object_path=f"objects/{source.sha256[:2]}/{source.sha256}",
        media_type=requirement.media_type,
        sha256=source.sha256,
        size_bytes=source.size_bytes,
        duration_ms=(
            0 if requirement.kind == "IMAGE" else cast(RealAudioTechnicalRecord, audio).duration_ms
        ),
        source_authority=item.source_authority,
        provenance_record_sha256=item.provenance_record_sha256,
        technical_profile=requirement.technical_profile,
        technical_record_sha256=technical_record_sha256,
        image=image,
        audio=audio,
    )
    return source, descriptor


def assess_real_asset_submission(
    *,
    submission: CreativeSampleRealAssetSubmission,
    source_root: Path,
) -> CreativeSampleRealAssetGapReport:
    """Inspect only explicitly submitted rows and retain all unresolved rows in one report."""
    template = build_real_asset_intake_template()
    _validate_submission_closure(template, submission)
    try:
        source = validate_local_path(source_root, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if not source.is_dir():
        raise RealAssetIntakeError("intake source root must be a local directory")
    declared_files = tuple(
        item.logical_path for item in submission.items if item.status == "SUBMITTED"
    )
    actual_files, actual_directories = _scan_exact_tree(source)
    if not actual_files <= frozenset(declared_files) or not actual_directories <= (
        _expected_directories(declared_files)
    ):
        raise RealAssetIntakeError("intake root contains an undeclared file or directory")
    rows: list[RealAssetGapRow] = []
    for requirement, item in zip(template.requirements, submission.items, strict=True):
        if item.status == "MISSING":
            disposition = "MISSING"
            failures = ("本地素材尚未由用户显式提交，不能推断、搜索或自动批准。",)
        else:
            candidate = source.joinpath(*PurePosixPath(item.logical_path).parts)
            if not os.path.lexists(candidate):
                disposition = "IDENTITY_MISMATCH"
                failures = ("显式提交的本地文件不存在或其精确路径不匹配。",)
            else:
                try:
                    _inspect_submitted_item(
                        requirement=requirement,
                        item=item,
                        source_root=source,
                        template=template,
                    )
                except RealAssetIntakeError:
                    disposition = "TECHNICAL_REJECTED"
                    failures = ("精确字节、媒体结构或技术质量未通过离线门禁。",)
                else:
                    disposition = "REVIEW_PENDING"
                    failures = ("技术门禁通过；仍缺同一冻结字节上的两份独立权利复核。",)
        rows.append(
            RealAssetGapRow(
                ordinal=requirement.ordinal,
                requirement_id=requirement.requirement_id,
                logical_path=requirement.logical_path,
                disposition=cast(
                    Literal[
                        "MISSING",
                        "IDENTITY_MISMATCH",
                        "TECHNICAL_REJECTED",
                        "REVIEW_PENDING",
                        "DISPUTED",
                        "EXPIRED",
                        "APPROVED",
                    ],
                    disposition,
                ),
                failures=failures,
                replacement_guidance=requirement.substitution_options,
            )
        )
    dispositions = tuple(item.disposition for item in rows)
    missing_count = dispositions.count("MISSING")
    rejected_count = sum(
        item in {"IDENTITY_MISMATCH", "TECHNICAL_REJECTED", "DISPUTED", "EXPIRED"}
        for item in dispositions
    )
    pending_count = dispositions.count("REVIEW_PENDING")
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-gap-report",
        "profile": INTAKE_PROFILE,
        "template_id": template.template_id,
        "submission_id": submission.submission_id,
        "rows": tuple(item.model_dump(mode="json") for item in rows),
        "missing_count": missing_count,
        "rejected_count": rejected_count,
        "pending_count": pending_count,
        "approved_count": 0,
        "current_gate": "HUMAN_GATE",
        "ready_for_rights_review": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetGapReport(
        report_id=stable_id("real_asset_gap_report", canonical),
        template_id=template.template_id,
        submission_id=submission.submission_id,
        rows=tuple(rows),
        missing_count=missing_count,
        rejected_count=rejected_count,
        pending_count=pending_count,
        approved_count=0,
    )


def _build_frozen_manifest(
    *,
    template: CreativeSampleRealAssetIntakeTemplate,
    submission: CreativeSampleRealAssetSubmission,
    objects: tuple[FrozenRealAssetDescriptor, ...],
) -> CreativeSampleFrozenRealAssetPackManifest:
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-frozen-real-asset-pack",
        "profile": INTAKE_PROFILE,
        "template_id": template.template_id,
        "submission_id": submission.submission_id,
        "pilot_pack_id": template.pilot_pack_id,
        "objects": tuple(item.model_dump(mode="json") for item in objects),
        "total_size_bytes": sum(item.size_bytes for item in objects),
        "state": "FROZEN_UNREVIEWED",
        "current_gate": "HUMAN_GATE",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleFrozenRealAssetPackManifest(
        pack_id=stable_id("real_asset_pack", canonical),
        template_id=template.template_id,
        submission_id=submission.submission_id,
        pilot_pack_id=template.pilot_pack_id,
        objects=objects,
        total_size_bytes=sum(item.size_bytes for item in objects),
    )


def _write_new_blob(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise RealAssetIntakeError("immutable intake object could not be published") from exc


def _cleanup_stage(stage: Path, relative_files: tuple[str, ...]) -> None:
    for logical in relative_files:
        try:
            stage.joinpath(*PurePosixPath(logical).parts).unlink(missing_ok=True)
        except OSError:
            pass
    directories = sorted(
        _expected_directories(relative_files),
        key=lambda value: (value.count("/"), value),
        reverse=True,
    )
    for logical in directories:
        try:
            stage.joinpath(*PurePosixPath(logical).parts).rmdir()
        except OSError:
            pass
    try:
        stage.rmdir()
    except OSError:
        pass


def freeze_real_asset_candidate_pack(
    *,
    submission: CreativeSampleRealAssetSubmission,
    source_root: Path,
    output_parent: Path,
) -> FrozenRealAssetPack:
    """Freeze all fourteen explicit local inputs.  This never performs a review or Provider call."""
    template = build_real_asset_intake_template()
    _validate_submission_closure(template, submission)
    if any(item.status != "SUBMITTED" for item in submission.items):
        raise RealAssetIntakeError("a partial intake cannot publish an immutable candidate pack")
    try:
        source = validate_local_path(source_root, must_exist=True)
        destination_parent = validate_local_path(output_parent, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if not source.is_dir() or not destination_parent.is_dir():
        raise RealAssetIntakeError("intake source and output parent must be local directories")
    if (
        source == destination_parent
        or source.is_relative_to(destination_parent)
        or (destination_parent.is_relative_to(source))
    ):
        raise RealAssetIntakeError("intake source and immutable output trees must not overlap")
    expected_files = tuple(item.logical_path for item in template.requirements)
    actual_files, actual_directories = _scan_exact_tree(source)
    if actual_files != frozenset(expected_files) or actual_directories != _expected_directories(
        expected_files
    ):
        raise RealAssetIntakeError(
            "local intake root does not have the exact fourteen-file closure"
        )
    sources: list[SafeLocalFile] = []
    descriptors: list[FrozenRealAssetDescriptor] = []
    for requirement, item in zip(template.requirements, submission.items, strict=True):
        source_file, descriptor = _inspect_submitted_item(
            requirement=requirement,
            item=item,
            source_root=source,
            template=template,
        )
        sources.append(source_file)
        descriptors.append(descriptor)
    manifest = _build_frozen_manifest(
        template=template,
        submission=submission,
        objects=tuple(descriptors),
    )
    final = destination_parent / manifest.pack_id
    if os.path.lexists(final):
        verified = verify_real_asset_candidate_pack(final)
        if verified.manifest != manifest:
            raise RealAssetIntakeError("existing pack identity conflicts with candidate bytes")
        return FrozenRealAssetPack(
            root=final,
            manifest_path=final / INTAKE_PACK_NAME,
            manifest=verified.manifest,
            created=False,
        )
    stage = Path(tempfile.mkdtemp(prefix=f".{manifest.pack_id}-", dir=destination_parent))
    relative_files = tuple(item.object_path for item in manifest.objects) + (INTAKE_PACK_NAME,)
    try:
        for source_file, descriptor in zip(sources, manifest.objects, strict=True):
            _write_new_blob(
                stage.joinpath(*PurePosixPath(descriptor.object_path).parts),
                source_file.data,
            )
        _write_new_blob(stage / INTAKE_PACK_NAME, _canonical_document(manifest))
        os.replace(stage, final)
    except Exception:
        _cleanup_stage(stage, relative_files)
        raise
    verified = verify_real_asset_candidate_pack(final)
    if verified.manifest != manifest:
        raise RealAssetIntakeError("published candidate pack failed exact verification")
    return FrozenRealAssetPack(
        root=final,
        manifest_path=final / INTAKE_PACK_NAME,
        manifest=manifest,
        created=True,
    )


def verify_real_asset_candidate_pack(root: Path) -> FrozenRealAssetPack:
    """Verify the immutable manifest and exact fourteen-object local closure."""
    try:
        absolute = validate_local_path(root, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if not absolute.is_dir():
        raise RealAssetIntakeError("real asset pack root must be a local directory")
    manifest = cast(
        CreativeSampleFrozenRealAssetPackManifest,
        _read_strict_json(absolute / INTAKE_PACK_NAME, CreativeSampleFrozenRealAssetPackManifest),
    )
    if absolute.name != manifest.pack_id:
        raise RealAssetIntakeError("real asset pack root name must equal its immutable pack ID")
    template = build_real_asset_intake_template()
    if (
        manifest.template_id != template.template_id
        or manifest.pilot_pack_id != template.pilot_pack_id
    ):
        raise RealAssetIntakeError("real asset pack does not bind the exact frozen Pilot intake")
    expected_bindings = tuple(
        (item.requirement_id, item.logical_path, item.kind, item.subject_id)
        for item in template.requirements
    )
    actual_bindings = tuple(
        (item.requirement_id, item.logical_path, item.kind, item.subject_id)
        for item in manifest.objects
    )
    if actual_bindings != expected_bindings:
        raise RealAssetIntakeError("real asset pack descriptor closure drifted from the template")
    expected_files = tuple(item.object_path for item in manifest.objects) + (INTAKE_PACK_NAME,)
    actual_files, actual_directories = _scan_exact_tree(absolute)
    if actual_files != frozenset(expected_files) or actual_directories != _expected_directories(
        expected_files
    ):
        raise RealAssetIntakeError("real asset pack filesystem closure is not exact")
    for requirement, descriptor in zip(template.requirements, manifest.objects, strict=True):
        object_path = absolute.joinpath(*PurePosixPath(descriptor.object_path).parts)
        try:
            if descriptor.kind == "IMAGE":
                source, observed_raw = inspect_png(
                    object_path,
                    forbidden_sha256=template.forbidden_fixture_sha256,
                )
                observed_image = RealImageTechnicalRecord(**asdict(observed_raw))
                observed_audio = None
            elif descriptor.kind == "VOICE":
                assert requirement.start_ms is not None and requirement.end_ms is not None
                source, observed_raw_audio = inspect_voice_wav(
                    object_path,
                    maximum_duration_ms=requirement.end_ms - requirement.start_ms,
                )
                observed_image = None
                observed_audio = RealAudioTechnicalRecord(**asdict(observed_raw_audio))
            else:
                source, observed_raw_audio = inspect_bgm_wav(object_path)
                observed_image = None
                observed_audio = RealAudioTechnicalRecord(**asdict(observed_raw_audio))
        except RealAssetMediaError as exc:
            raise RealAssetIntakeError("real asset pack object could not be verified") from exc
        if source.sha256 != descriptor.sha256 or source.size_bytes != descriptor.size_bytes:
            raise RealAssetIntakeError("real asset pack object identity drifted")
        if descriptor.image != observed_image or descriptor.audio != observed_audio:
            raise RealAssetIntakeError("real asset pack technical evidence did not reproduce")
    return FrozenRealAssetPack(
        root=absolute,
        manifest_path=absolute / INTAKE_PACK_NAME,
        manifest=manifest,
        created=False,
    )


def load_real_asset_rights_manifest(path: Path) -> CreativeSampleRealAssetRightsManifest:
    return cast(
        CreativeSampleRealAssetRightsManifest,
        _read_strict_json(path, CreativeSampleRealAssetRightsManifest),
    )


def build_real_asset_rights_manifest(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    reviews: tuple[RealAssetRightsReview, ...],
) -> CreativeSampleRealAssetRightsManifest:
    """Bind explicit review records; this does not decide or authorize Provider execution."""
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-rights-manifest",
        "profile": INTAKE_PROFILE,
        "pack_id": pack.pack_id,
        "reviews": tuple(item.model_dump(mode="json") for item in reviews),
        "status": "REVIEW_CANDIDATE",
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    return CreativeSampleRealAssetRightsManifest(
        manifest_id=stable_id("real_asset_rights", canonical),
        pack_id=pack.pack_id,
        reviews=reviews,
    )


def _validate_rights_closure(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    rights: CreativeSampleRealAssetRightsManifest,
    evaluated_at: str,
) -> None:
    evaluated = _parse_utc(_utc_seconds(evaluated_at, field="evaluated_at"))
    if rights.pack_id != pack.pack_id:
        raise RealAssetIntakeError("rights manifest does not bind the exact frozen asset pack")
    for object_index, descriptor in enumerate(pack.objects):
        reviewer_a, reviewer_b = rights.reviews[object_index * 2 : object_index * 2 + 2]
        for review in (reviewer_a, reviewer_b):
            if (
                review.pack_id != pack.pack_id
                or review.requirement_id != descriptor.requirement_id
                or review.logical_path != descriptor.logical_path
                or review.media_sha256 != descriptor.sha256
                or review.media_size_bytes != descriptor.size_bytes
                or review.provenance_record_sha256 != descriptor.provenance_record_sha256
                or review.technical_record_sha256 != descriptor.technical_record_sha256
                or review.source_authority != descriptor.source_authority
            ):
                raise RealAssetIntakeError("rights review drifted from its exact frozen object")
            if review.decision != "APPROVED":
                raise RealAssetIntakeError("a rejected rights record remains at HUMAN_GATE")
            if _parse_utc(review.reviewed_at) > evaluated:
                raise RealAssetIntakeError("rights review is in the future relative to evaluation")
            if review.valid_until != "PERPETUAL" and evaluated >= _parse_utc(review.valid_until):
                raise RealAssetIntakeError("rights validity uses an expired exclusive boundary")
        if reviewer_a.reviewer_ref_sha256 == reviewer_b.reviewer_ref_sha256:
            raise RealAssetIntakeError("one person cannot fill both independent review roles")
        if reviewer_a.review_record_sha256 == reviewer_b.review_record_sha256:
            raise RealAssetIntakeError("independent reviews must retain distinct record digests")
        agreement_fields = (
            "media_sha256",
            "media_size_bytes",
            "provenance_record_sha256",
            "technical_record_sha256",
            "source_authority",
            "copyright_basis",
            "likeness_basis",
            "privacy_basis",
            "territory",
            "use_scope",
            "valid_until",
            "provenance_approved",
            "copyright_approved",
            "likeness_approved",
            "privacy_approved",
            "territory_approved",
            "use_scope_approved",
            "content_role_approved",
            "decision",
        )
        if any(
            getattr(reviewer_a, field) != getattr(reviewer_b, field) for field in agreement_fields
        ):
            raise RealAssetIntakeError("the two rights reviewers disagree on the exact usage scope")


def _approval_ref(*, descriptor: FrozenRealAssetDescriptor, rights_manifest_id: str) -> str:
    return stable_id(
        "intake_approval",
        {
            "media_sha256": descriptor.sha256,
            "requirement_id": descriptor.requirement_id,
            "rights_manifest_id": rights_manifest_id,
            "technical_record_sha256": descriptor.technical_record_sha256,
        },
    )


def _derive_real_spec(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    rights_manifest_id: str,
) -> CreativeSampleSpec:
    pilot_spec, _ = build_creative_sample_pilot_documents()
    image_by_subject = {item.subject_id: item for item in pack.objects if item.kind == "IMAGE"}
    character_bibles: list[CharacterBible] = []
    for character_bible in pilot_spec.character_bibles:
        descriptor = image_by_subject.get(character_bible.character_id)
        if descriptor is None:
            raise RealAssetIntakeError("real pack lacks one exact character reference")
        approval_ref = _approval_ref(
            descriptor=descriptor,
            rights_manifest_id=rights_manifest_id,
        )
        version_id = CharacterAssetVersion.derive_id(
            character_id=character_bible.character_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=character_bible.visual_description,
        )
        character_version = CharacterAssetVersion(
            id=version_id,
            character_id=character_bible.character_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=character_bible.visual_description,
        )
        character_bibles.append(
            CharacterBible(
                character_id=character_bible.character_id,
                name=character_bible.name,
                visual_description=character_bible.visual_description,
                asset_versions=(character_version,),
                active_asset_version_id=character_version.id,
            )
        )
    scene_bibles: list[SceneBible] = []
    for scene_bible in pilot_spec.scene_bibles:
        descriptor = image_by_subject.get(scene_bible.scene_id)
        if descriptor is None:
            raise RealAssetIntakeError("real pack lacks one exact scene reference")
        approval_ref = _approval_ref(
            descriptor=descriptor,
            rights_manifest_id=rights_manifest_id,
        )
        version_id = SceneAssetVersion.derive_id(
            scene_id=scene_bible.scene_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=scene_bible.visual_description,
        )
        scene_version = SceneAssetVersion(
            id=version_id,
            scene_id=scene_bible.scene_id,
            version=2,
            content_sha256=descriptor.sha256,
            media_type="image/png",
            approval_ref=approval_ref,
            visual_description=scene_bible.visual_description,
        )
        scene_bibles.append(
            SceneBible(
                scene_id=scene_bible.scene_id,
                ordinal=scene_bible.ordinal,
                name=scene_bible.name,
                visual_description=scene_bible.visual_description,
                asset_versions=(scene_version,),
                active_asset_version_id=scene_version.id,
            )
        )
    return CreativeSampleSpec(
        title=pilot_spec.title,
        seed=pilot_spec.seed,
        duration_ms=pilot_spec.duration_ms,
        character_bibles=tuple(character_bibles),
        scene_bibles=tuple(scene_bibles),
        dialogue=pilot_spec.dialogue,
        shots=pilot_spec.shots,
    )


def _derive_revision(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    rights: CreativeSampleRealAssetRightsManifest,
    evaluated_at: str,
) -> tuple[CreativeSampleRealAssetSpecDocument, CreativeSampleRealAssetRevision]:
    _validate_rights_closure(pack=pack, rights=rights, evaluated_at=evaluated_at)
    pilot_spec, pilot = build_creative_sample_pilot_documents()
    real_spec = _derive_real_spec(pack=pack, rights_manifest_id=rights.manifest_id)
    compilation = compile_creative_sample(real_spec)
    ordered_shot_ids = tuple(item.id for item in compilation.pir.shots)
    old_asset_ids = set(pilot.active_asset_version_ids)
    old_asset_digests = {item.placeholder_sha256 for item in pilot.asset_requirements}
    new_versions = tuple(
        version for bible in real_spec.character_bibles for version in bible.asset_versions
    ) + tuple(version for bible in real_spec.scene_bibles for version in bible.asset_versions)
    if old_asset_ids & {item.id for item in new_versions}:
        raise RealAssetIntakeError("real specification inherited a fixture asset identity")
    if old_asset_digests & {item.content_sha256 for item in new_versions}:
        raise RealAssetIntakeError("real specification inherited a fixture asset digest")
    if any(item.approval_ref.startswith("pilot-fixture-only-") for item in new_versions):
        raise RealAssetIntakeError("real specification inherited a fixture approval reference")
    if _model_sha256(real_spec) == _model_sha256(pilot_spec):
        raise RealAssetIntakeError("real specification must have a new canonical identity")
    if compilation.id == pilot.compilation_id:
        raise RealAssetIntakeError("real compilation must differ from the fixture compilation")
    if len(ordered_shot_ids) != 10 or any(
        current == predecessor
        for current, predecessor in zip(ordered_shot_ids, pilot.ordered_shot_ids, strict=True)
    ):
        raise RealAssetIntakeError("every real-media shot identity must differ from its fixture")
    spec_document = CreativeSampleRealAssetSpecDocument(
        asset_pack_id=pack.pack_id,
        rights_manifest_id=rights.manifest_id,
        spec=real_spec,
    )
    audio_bindings = tuple(item for item in pack.objects if item.kind in {"VOICE", "BGM"})
    canonical: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": "sdc.creative-sample-real-asset-revision",
        "profile": INTAKE_PROFILE,
        "revision_number": 2,
        "predecessor_pilot_pack_id": pilot.pack_id,
        "predecessor_spec_sha256": _model_sha256(pilot_spec),
        "predecessor_compilation_id": pilot.compilation_id,
        "predecessor_shot_ids": pilot.ordered_shot_ids,
        "asset_pack_id": pack.pack_id,
        "rights_manifest_id": rights.manifest_id,
        "evaluated_at": evaluated_at,
        "real_spec_sha256": _model_sha256(real_spec),
        "real_spec_document_sha256": _sha256(_canonical_document(spec_document)),
        "real_spec": real_spec.model_dump(mode="json"),
        "compilation": compilation.model_dump(mode="json"),
        "ordered_shot_ids": ordered_shot_ids,
        "audio_bindings": tuple(item.model_dump(mode="json") for item in audio_bindings),
        "decision": "PASS_ASSET_INTAKE_ONLY",
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_separate_provider_approval": True,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    revision = CreativeSampleRealAssetRevision(
        revision_id=stable_id("real_asset_revision", canonical),
        predecessor_pilot_pack_id=pilot.pack_id,
        predecessor_spec_sha256=_model_sha256(pilot_spec),
        predecessor_compilation_id=pilot.compilation_id,
        predecessor_shot_ids=pilot.ordered_shot_ids,
        asset_pack_id=pack.pack_id,
        rights_manifest_id=rights.manifest_id,
        evaluated_at=evaluated_at,
        real_spec_sha256=_model_sha256(real_spec),
        real_spec_document_sha256=_sha256(_canonical_document(spec_document)),
        real_spec=real_spec,
        compilation=compilation,
        ordered_shot_ids=ordered_shot_ids,
        audio_bindings=audio_bindings,
    )
    return spec_document, revision


def qualify_real_asset_candidate_pack(
    *,
    pack_root: Path,
    rights: CreativeSampleRealAssetRightsManifest,
    output_parent: Path,
    evaluated_at: str,
) -> QualifiedRealAssetRevision:
    """Derive a new candidate revision after exact double review; still zero authority."""
    frozen = verify_real_asset_candidate_pack(pack_root)
    spec_document, revision = _derive_revision(
        pack=frozen.manifest,
        rights=rights,
        evaluated_at=evaluated_at,
    )
    try:
        parent = validate_local_path(output_parent, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if not parent.is_dir():
        raise RealAssetIntakeError("qualified revision output parent must be a local directory")
    if (
        parent == frozen.root
        or parent.is_relative_to(frozen.root)
        or frozen.root.is_relative_to(parent)
    ):
        raise RealAssetIntakeError("qualified revision and immutable media pack must not overlap")
    final = parent / revision.revision_id
    if os.path.lexists(final):
        verified = verify_qualified_real_asset_revision(final, pack_root=frozen.root)
        if verified.revision != revision:
            raise RealAssetIntakeError("existing revision identity conflicts with reviewed inputs")
        return QualifiedRealAssetRevision(
            root=final,
            revision_path=final / INTAKE_REVISION_NAME,
            revision=revision,
            created=False,
        )
    stage = Path(tempfile.mkdtemp(prefix=f".{revision.revision_id}-", dir=parent))
    relative_files = (INTAKE_REAL_SPEC_NAME, INTAKE_RIGHTS_NAME, INTAKE_REVISION_NAME)
    try:
        _write_new_blob(stage / INTAKE_REAL_SPEC_NAME, _canonical_document(spec_document))
        _write_new_blob(stage / INTAKE_RIGHTS_NAME, _canonical_document(rights))
        _write_new_blob(stage / INTAKE_REVISION_NAME, _canonical_document(revision))
        os.replace(stage, final)
    except Exception:
        _cleanup_stage(stage, relative_files)
        raise
    verified = verify_qualified_real_asset_revision(final, pack_root=frozen.root)
    if verified.revision != revision:
        raise RealAssetIntakeError("published real-asset revision failed exact verification")
    return QualifiedRealAssetRevision(
        root=final,
        revision_path=final / INTAKE_REVISION_NAME,
        revision=revision,
        created=True,
    )


def verify_qualified_real_asset_revision(
    root: Path, *, pack_root: Path
) -> QualifiedRealAssetRevision:
    try:
        absolute = validate_local_path(root, must_exist=True)
    except CreativeMediaError as exc:
        raise RealAssetIntakeError(str(exc)) from exc
    if not absolute.is_dir():
        raise RealAssetIntakeError("qualified revision root must be a local directory")
    expected_files = (INTAKE_REAL_SPEC_NAME, INTAKE_RIGHTS_NAME, INTAKE_REVISION_NAME)
    files, directories = _scan_exact_tree(absolute)
    if files != frozenset(expected_files) or directories:
        raise RealAssetIntakeError("qualified revision directory does not have an exact closure")
    spec_document = cast(
        CreativeSampleRealAssetSpecDocument,
        _read_strict_json(absolute / INTAKE_REAL_SPEC_NAME, CreativeSampleRealAssetSpecDocument),
    )
    rights = load_real_asset_rights_manifest(absolute / INTAKE_RIGHTS_NAME)
    revision = cast(
        CreativeSampleRealAssetRevision,
        _read_strict_json(absolute / INTAKE_REVISION_NAME, CreativeSampleRealAssetRevision),
    )
    if absolute.name != revision.revision_id:
        raise RealAssetIntakeError("qualified revision root name must equal its revision ID")
    frozen = verify_real_asset_candidate_pack(pack_root)
    if spec_document.asset_pack_id != frozen.manifest.pack_id:
        raise RealAssetIntakeError("qualified specification binds a different asset pack")
    if spec_document.rights_manifest_id != rights.manifest_id:
        raise RealAssetIntakeError("qualified specification binds a different rights manifest")
    rebuilt_document, rebuilt_revision = _derive_revision(
        pack=frozen.manifest,
        rights=rights,
        evaluated_at=revision.evaluated_at,
    )
    if spec_document != rebuilt_document or revision != rebuilt_revision:
        raise RealAssetIntakeError(
            "qualified revision does not match an exact deterministic rebuild"
        )
    return QualifiedRealAssetRevision(
        root=absolute,
        revision_path=absolute / INTAKE_REVISION_NAME,
        revision=revision,
        created=False,
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the offline all-missing real asset intake")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    template_path, gap_path = write_real_asset_intake_templates(args.output)
    print(
        json.dumps(
            {
                "current_gate": "HUMAN_GATE",
                "gap_report": gap_path.name,
                "posts_allowed": 0,
                "provider_requests": 0,
                "template": template_path.name,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "CreativeSampleFrozenRealAssetPackManifest",
    "CreativeSampleRealAssetGapReport",
    "CreativeSampleRealAssetIntakeTemplate",
    "CreativeSampleRealAssetRevision",
    "CreativeSampleRealAssetRightsManifest",
    "CreativeSampleRealAssetSpecDocument",
    "CreativeSampleRealAssetSubmission",
    "FrozenRealAssetPack",
    "QualifiedRealAssetRevision",
    "RealAssetIntakeError",
    "RealAssetRequirement",
    "RealAssetRightsReview",
    "RealAssetSubmissionItem",
    "assess_real_asset_submission",
    "build_missing_real_asset_submission",
    "build_real_asset_gap_report",
    "build_real_asset_intake_template",
    "build_real_asset_rights_manifest",
    "build_real_asset_submission",
    "freeze_real_asset_candidate_pack",
    "load_real_asset_intake_template",
    "load_real_asset_rights_manifest",
    "load_real_asset_submission",
    "qualify_real_asset_candidate_pack",
    "verify_qualified_real_asset_revision",
    "verify_real_asset_candidate_pack",
    "write_real_asset_intake_templates",
]


if __name__ == "__main__":
    raise SystemExit(_main())
