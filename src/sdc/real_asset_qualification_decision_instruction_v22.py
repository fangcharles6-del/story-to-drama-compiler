"""Pure retained-instruction contract for trusted local qualification finalization v2.2."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal
from unicodedata import normalize

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sdc.compiler import stable_id
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    QUALIFICATION_V2_POLICY_ID,
    QUALIFICATION_V2_POLICY_VERSION,
    RealAssetQualificationDecisionV2,
    RealAssetQualificationIssueCodeV2,
)

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
_ISSUE_ORDER: tuple[RealAssetQualificationIssueCodeV2, ...] = (
    "EVIDENCE_SCOPE_UNCLEAR",
    "POLICY_REQUIREMENT_NOT_MET",
    "QUALIFIER_REJECTED_ASSET_INTAKE",
    "OTHER_BLOCKING_ISSUE",
)


def _canonical_utc_seconds(value: str, *, field: str) -> str:
    if _UTC_SECONDS.fullmatch(value) is None:
        raise ValueError(f"{field} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid UTC timestamp") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError(f"{field} must be canonical UTC seconds")
    return value


class CreativeSampleRealAssetQualificationDecisionInstructionV22(BaseModel):
    """A retained, zero-authority instruction for one independent scoped decision."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )

    schema_version: Literal["2.2.0"] = "2.2.0"
    document_type: Literal[
        "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
    ] = "sdc.creative-sample-real-asset-qualification-decision-instruction-v2.2"
    profile: Literal[
        "creative-sample-real-asset-qualification-decision-finalization-v2.2"
    ] = "creative-sample-real-asset-qualification-decision-finalization-v2.2"
    instruction_id: str = Field(
        pattern=r"^real_asset_qualification_decision_instruction_v22_[0-9a-f]{20}$"
    )
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    policy_id: Literal[
        "creative-sample-real-asset-qualification-policy"
    ] = QUALIFICATION_V2_POLICY_ID
    policy_version: Literal["2.0.0"] = QUALIFICATION_V2_POLICY_VERSION
    policy_document_sha256: Literal[
        "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
    ] = QUALIFICATION_V2_POLICY_DOCUMENT_SHA256
    qualification_scope: Literal["ASSET_INTAKE_ONLY"] = "ASSET_INTAKE_ONLY"
    qualifier_role: Literal["INDEPENDENT_QUALIFIER"] = "INDEPENDENT_QUALIFIER"
    qualifier_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    decision_at: str
    decision: RealAssetQualificationDecisionV2
    qualification_issue_codes: tuple[RealAssetQualificationIssueCodeV2, ...] = Field(
        max_length=4,
    )
    qualification_basis: str = Field(min_length=1, max_length=1000)
    status: Literal["DECISION_INSTRUCTION_RECORDED"] = "DECISION_INSTRUCTION_RECORDED"
    rights_manifest_created: Literal[False] = False
    rights_qualification_performed: Literal[False] = False
    eligible_for_separate_manifest_design_review: Literal[False] = False
    current_gate: Literal["HUMAN_GATE"] = "HUMAN_GATE"
    provider_state: Literal["NOT_AUTHORIZED"] = "NOT_AUTHORIZED"
    eligible_for_real_generation: Literal[False] = False
    execution_authorized: Literal[False] = False
    posts_allowed: Literal[0] = 0
    provider_requests: Literal[0] = 0

    @field_validator("decision_at")
    @classmethod
    def validate_decision_at(cls, value: str) -> str:
        return _canonical_utc_seconds(value, field="decision_at")

    @field_validator("qualification_basis")
    @classmethod
    def validate_qualification_basis(cls, value: str) -> str:
        if value != value.strip() or value != normalize("NFC", value):
            raise ValueError("qualification basis must be trimmed NFC text")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("qualification basis must not contain control characters")
        return value

    @field_validator("qualification_issue_codes")
    @classmethod
    def validate_issue_codes(
        cls,
        value: tuple[RealAssetQualificationIssueCodeV2, ...],
    ) -> tuple[RealAssetQualificationIssueCodeV2, ...]:
        if len(value) != len(set(value)):
            raise ValueError("qualification issue codes must be unique")
        if value != tuple(code for code in _ISSUE_ORDER if code in value):
            raise ValueError("qualification issue codes must use canonical order")
        return value

    @model_validator(mode="after")
    def validate_instruction(
        self,
    ) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
        positive = self.decision == "PASS_ASSET_INTAKE_ONLY"
        if positive == bool(self.qualification_issue_codes):
            raise ValueError(
                "positive decisions require no issue; negative decisions require an issue"
            )
        rejected_code = "QUALIFIER_REJECTED_ASSET_INTAKE"
        if self.decision == "REJECTED" and rejected_code not in self.qualification_issue_codes:
            raise ValueError("rejected decisions require the qualifier rejection issue code")
        if (
            self.decision == "NEEDS_HUMAN_REVIEW"
            and rejected_code in self.qualification_issue_codes
        ):
            raise ValueError("human-review decisions cannot contain the qualifier rejection code")
        expected_id = stable_id(
            "real_asset_qualification_decision_instruction_v22",
            self.model_dump(mode="json", exclude={"instruction_id"}),
        )
        if self.instruction_id != expected_id:
            raise ValueError("instruction ID must bind its complete canonical content")
        return self


__all__ = ["CreativeSampleRealAssetQualificationDecisionInstructionV22"]
