"""Pure Pack-level Rights Manifest v2.4 contracts and in-memory verification.

This module consumes an exact positive Human Review v2 qualification closure.  It records
rights-manifest creation for the frozen Pack, but deliberately grants no generation, runtime,
Provider, posting, entitlement, or authorization capability.  The API performs no file or
network I/O and never reads a clock; ``manifest_at`` is always explicit caller input.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from sdc.compiler import stable_id
from sdc.real_asset_intake import CreativeSampleFrozenRealAssetPackManifest
from sdc.real_asset_qualification_decision_instruction_v22 import (
    CreativeSampleRealAssetQualificationDecisionInstructionV22,
)
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
    CreativeSampleRealAssetQualificationRequestV2,
    RealAssetQualificationV2Error,
    verify_real_asset_qualification_closure_v2,
)
from sdc.real_asset_review_v2 import (
    CreativeSampleRealAssetHumanPackReviewV2,
    CreativeSampleRealAssetReviewPairCheckV2,
    CreativeSampleRealAssetRightsEvidenceBundleV2,
)

RIGHTS_MANIFEST_V2_PROFILE: Literal[
    "creative-sample-real-asset-rights-manifest-consumer-v2.4"
] = "creative-sample-real-asset-rights-manifest-consumer-v2.4"
RIGHTS_MANIFEST_V2_POLICY_ID: Literal[
    "creative-sample-real-asset-rights-manifest-policy"
] = "creative-sample-real-asset-rights-manifest-policy"
RIGHTS_MANIFEST_V2_POLICY_VERSION: Literal["2.4.0"] = "2.4.0"

_LOWER_SHA256 = r"^[0-9a-f]{64}$"
_UTC_SECONDS = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
_JSON_LIMIT = 1_048_576
_POLICY_DIGEST_DOMAIN = b"sdc:creative-sample-real-asset-rights-manifest-policy:v2.4\0"


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


_RIGHTS_MANIFEST_POLICY_PAYLOAD: dict[str, object] = {
    "policy_id": RIGHTS_MANIFEST_V2_POLICY_ID,
    "policy_version": RIGHTS_MANIFEST_V2_POLICY_VERSION,
    "positive_decision": "PASS_ASSET_INTAKE_ONLY",
    "qualification_scope": "ASSET_INTAKE_ONLY",
    "rules": (
        "EXACT_V2_UPSTREAM_CANONICAL_CLOSURE",
        "EXACT_RETAINED_INSTRUCTION_BINDING",
        "MANIFEST_AT_NOT_BEFORE_DECISION",
        "EVIDENCE_VALID_AT_MANIFEST",
        "MANIFEST_RECORDS_RIGHTS_ONLY",
        "NO_GENERATION_NO_EXECUTION_NO_PROVIDER_AUTHORIZATION",
    ),
}
RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256: Literal[
    "ac31acb7faf86d08752ec37a585d12754af7611d252e8112b41088f3ed71d912"
] = "ac31acb7faf86d08752ec37a585d12754af7611d252e8112b41088f3ed71d912"
if (
    _sha256(_POLICY_DIGEST_DOMAIN + _canonical_payload(_RIGHTS_MANIFEST_POLICY_PAYLOAD))
    != RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256
):
    raise RuntimeError("Rights Manifest v2.4 policy payload digest drifted")


class RealAssetRightsManifestV24Error(RuntimeError):
    """The pure Rights Manifest v2.4 consumer failed closed."""


class _RightsManifestV24Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


def _utc_seconds(value: str, *, field: str) -> str:
    if __import__("re").fullmatch(_UTC_SECONDS, value) is None:
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


class CreativeSampleRealAssetRightsManifestV2(_RightsManifestV24Model):
    """A Pack-level rights record that carries exactly zero execution authority."""

    schema_version: Literal["2.4.0"]
    document_type: Literal["sdc.creative-sample-real-asset-rights-manifest-v2"]
    profile: Literal["creative-sample-real-asset-rights-manifest-consumer-v2.4"]
    manifest_id: str = Field(pattern=r"^real_asset_rights_manifest_v2_[0-9a-f]{20}$")
    manifest_at: str
    manifest_policy_id: Literal["creative-sample-real-asset-rights-manifest-policy"]
    manifest_policy_version: Literal["2.4.0"]
    manifest_policy_document_sha256: Literal[
        "ac31acb7faf86d08752ec37a585d12754af7611d252e8112b41088f3ed71d912"
    ]

    pack_id: str = Field(pattern=r"^real_asset_pack_[0-9a-f]{20}$")
    pack_manifest_sha256: str = Field(pattern=_LOWER_SHA256)
    rights_evidence_bundle_id: str = Field(
        pattern=r"^real_asset_rights_evidence_v2_[0-9a-f]{20}$"
    )
    rights_evidence_bundle_sha256: str = Field(pattern=_LOWER_SHA256)
    review_a_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_a_contract_sha256: str = Field(pattern=_LOWER_SHA256)
    review_b_id: str = Field(pattern=r"^real_asset_pack_review_v2_[0-9a-f]{20}$")
    review_b_contract_sha256: str = Field(pattern=_LOWER_SHA256)
    pair_check_id: str = Field(pattern=r"^real_asset_review_pair_check_v2_[0-9a-f]{20}$")
    pair_check_sha256: str = Field(pattern=_LOWER_SHA256)
    request_id: str = Field(pattern=r"^real_asset_qualification_request_v2_[0-9a-f]{20}$")
    request_sha256: str = Field(pattern=_LOWER_SHA256)
    instruction_id: str = Field(
        pattern=r"^real_asset_qualification_decision_instruction_v22_[0-9a-f]{20}$"
    )
    instruction_sha256: str = Field(pattern=_LOWER_SHA256)
    decision_id: str = Field(pattern=r"^real_asset_qualification_decision_v2_[0-9a-f]{20}$")
    decision_sha256: str = Field(pattern=_LOWER_SHA256)

    qualification_policy_id: Literal["creative-sample-real-asset-qualification-policy"]
    qualification_policy_version: Literal["2.0.0"]
    qualification_policy_document_sha256: Literal[
        "f6da348159f8ac4cc0a65000282445f5bd672dc9f2557b8969a02baa7982b031"
    ]
    evidence_valid_until: str
    evidence_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    evidence_preparer_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    review_a_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_a_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    review_b_record_sha256: str = Field(pattern=_LOWER_SHA256)
    reviewer_b_retained_record_sha256: str = Field(pattern=_LOWER_SHA256)
    qualifier_ref_sha256: str = Field(pattern=_LOWER_SHA256)
    qualifier_record_sha256: str = Field(pattern=_LOWER_SHA256)

    decision_at: str
    qualification_decision: Literal["PASS_ASSET_INTAKE_ONLY"]
    qualification_scope: Literal["ASSET_INTAKE_ONLY"]
    eligible_for_separate_manifest_design_review: Literal[True]
    status: Literal["RIGHTS_MANIFEST_CREATED"]
    rights_qualification_performed: Literal[True]
    rights_manifest_created: Literal[True]
    current_gate: Literal["HUMAN_GATE"]
    provider_state: Literal["NOT_AUTHORIZED"]
    eligible_for_real_generation: Literal[False]
    execution_authorized: Literal[False]
    posts_allowed: Literal[0]
    provider_requests: Literal[0]

    @model_validator(mode="before")
    @classmethod
    def validate_exact_scalar_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        boolean_fields = (
            "eligible_for_separate_manifest_design_review",
            "rights_qualification_performed",
            "rights_manifest_created",
            "eligible_for_real_generation",
            "execution_authorized",
        )
        for field in boolean_fields:
            if field in value and type(value[field]) is not bool:
                raise ValueError(f"{field} must be an exact JSON boolean")
        zero_fields = ("posts_allowed", "provider_requests")
        for field in zero_fields:
            if field in value and (type(value[field]) is not int or value[field] != 0):
                raise ValueError(f"{field} must be the exact JSON integer zero")
        return value

    @field_validator("manifest_at", "decision_at")
    @classmethod
    def validate_utc_seconds(cls, value: str, info: ValidationInfo) -> str:
        return _utc_seconds(value, field=info.field_name or "manifest timestamp")

    @field_validator("evidence_valid_until")
    @classmethod
    def validate_evidence_valid_until(cls, value: str) -> str:
        if value == "PERPETUAL":
            return value
        return _utc_seconds(value, field="evidence_valid_until")

    @model_validator(mode="after")
    def validate_manifest(self) -> CreativeSampleRealAssetRightsManifestV2:
        if self.manifest_policy_document_sha256 != RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256:
            raise ValueError("rights manifest must bind the built-in v2.4 policy document")
        manifest_at = _parse_utc(self.manifest_at)
        if manifest_at < _parse_utc(self.decision_at):
            raise ValueError("rights manifest cannot predate the qualification decision")
        if (
            self.evidence_valid_until != "PERPETUAL"
            and manifest_at >= _parse_utc(self.evidence_valid_until)
        ):
            raise ValueError("rights manifest requires evidence valid at manifest_at")

        contract_digests = {
            self.pack_manifest_sha256,
            self.rights_evidence_bundle_sha256,
            self.review_a_contract_sha256,
            self.review_b_contract_sha256,
            self.pair_check_sha256,
            self.request_sha256,
            self.instruction_sha256,
            self.decision_sha256,
            self.qualification_policy_document_sha256,
            self.manifest_policy_document_sha256,
            self.review_a_record_sha256,
            self.review_b_record_sha256,
        }
        if len(contract_digests) != 12:
            raise ValueError("rights manifest contract and review-record digests must be distinct")
        if self.qualifier_record_sha256 != self.instruction_sha256:
            raise ValueError("qualifier record must be the exact canonical retained instruction")
        retained_digests = {
            self.evidence_retained_record_sha256,
            self.evidence_preparer_ref_sha256,
            self.reviewer_a_retained_record_sha256,
            self.reviewer_b_retained_record_sha256,
            self.qualifier_ref_sha256,
        }
        if len(retained_digests) != 5 or retained_digests & contract_digests:
            raise ValueError("rights manifest retained records must be distinct and non-aliasing")

        expected_id = stable_id(
            "real_asset_rights_manifest_v2",
            self.model_dump(mode="json", exclude={"manifest_id"}),
        )
        if self.manifest_id != expected_id:
            raise ValueError("rights manifest ID must bind its complete canonical content")
        return self


def _revalidate[ModelT: BaseModel](value: ModelT, model: type[ModelT], *, field: str) -> ModelT:
    try:
        before = _canonical_document(value)
        rebuilt = model.model_validate(value.model_dump(mode="python"), strict=True)
        after = _canonical_document(rebuilt)
    except (AttributeError, TypeError, ValueError) as exc:
        raise RealAssetRightsManifestV24Error(f"{field} violates its strict contract") from exc
    if before != after:
        raise RealAssetRightsManifestV24Error(
            f"{field} changes canonical bytes during strict revalidation"
        )
    return rebuilt


def _verify_instruction_binding(
    *,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
) -> CreativeSampleRealAssetQualificationDecisionInstructionV22:
    instruction = _revalidate(
        instruction,
        CreativeSampleRealAssetQualificationDecisionInstructionV22,
        field="qualification instruction",
    )
    instruction_sha256 = _sha256(_canonical_document(instruction))
    if instruction_sha256 != decision.qualifier_record_sha256:
        raise RealAssetRightsManifestV24Error(
            "qualification decision does not bind the canonical retained instruction"
        )
    if (
        instruction.request_id != request.request_id
        or instruction.request_sha256 != _sha256(_canonical_document(request))
        or instruction.policy_id != request.policy_id
        or instruction.policy_version != request.policy_version
        or instruction.policy_document_sha256 != request.policy_document_sha256
        or instruction.qualification_scope != decision.qualification_scope
        or instruction.qualifier_ref_sha256 != decision.qualifier_ref_sha256
        or instruction.decision_at != decision.decision_at
        or instruction.decision != decision.decision
        or instruction.qualification_issue_codes != decision.qualification_issue_codes
        or instruction.qualification_basis != decision.qualification_basis
    ):
        raise RealAssetRightsManifestV24Error(
            "qualification instruction does not bind the exact request and decision"
        )
    return instruction


def _assert_pack_record_non_aliasing(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    closure_digests: set[str],
) -> None:
    pack_record_sequence = tuple(
        digest
        for descriptor in pack.objects
        for digest in (
            descriptor.sha256,
            descriptor.provenance_record_sha256,
            descriptor.technical_record_sha256,
        )
    )
    pack_record_digests = set(pack_record_sequence)
    if len(pack_record_sequence) != 42 or len(pack_record_digests) != 42:
        raise RealAssetRightsManifestV24Error(
            "Pack media, provenance, and technical record digests must be fully distinct"
        )
    if pack_record_digests & closure_digests:
        raise RealAssetRightsManifestV24Error(
            "manifest contracts and retained records must not alias Pack object records"
        )


def build_real_asset_rights_manifest_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
    manifest_at: str,
) -> CreativeSampleRealAssetRightsManifestV2:
    """Build one deterministic, inert manifest from an exact positive v2 closure."""

    pack = _revalidate(pack, CreativeSampleFrozenRealAssetPackManifest, field="frozen Pack")
    evidence = _revalidate(
        evidence,
        CreativeSampleRealAssetRightsEvidenceBundleV2,
        field="Evidence Bundle",
    )
    reviewer_a = _revalidate(
        reviewer_a,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer A contract",
    )
    reviewer_b = _revalidate(
        reviewer_b,
        CreativeSampleRealAssetHumanPackReviewV2,
        field="Reviewer B contract",
    )
    pair_check = _revalidate(
        pair_check,
        CreativeSampleRealAssetReviewPairCheckV2,
        field="PairCheck contract",
    )
    request = _revalidate(
        request,
        CreativeSampleRealAssetQualificationRequestV2,
        field="qualification request",
    )
    decision = _revalidate(
        decision,
        CreativeSampleRealAssetQualificationDecisionV2,
        field="qualification decision",
    )
    try:
        decision = verify_real_asset_qualification_closure_v2(
            pack=pack,
            evidence=evidence,
            reviewer_a=reviewer_a,
            reviewer_b=reviewer_b,
            pair_check=pair_check,
            request=request,
            decision=decision,
        )
    except (RealAssetQualificationV2Error, ValidationError, ValueError) as exc:
        raise RealAssetRightsManifestV24Error(
            "qualification closure failed exact deterministic verification"
        ) from exc
    instruction = _verify_instruction_binding(
        request=request,
        instruction=instruction,
        decision=decision,
    )
    if (
        decision.decision != "PASS_ASSET_INTAKE_ONLY"
        or decision.rights_qualification_performed is not True
        or decision.eligible_for_separate_manifest_design_review is not True
        or decision.current_gate != "HUMAN_GATE"
        or decision.provider_state != "NOT_AUTHORIZED"
    ):
        raise RealAssetRightsManifestV24Error(
            "qualification decision is not eligible for separate manifest design review"
        )

    try:
        manifest_at = _utc_seconds(manifest_at, field="manifest_at")
    except ValueError as exc:
        raise RealAssetRightsManifestV24Error("manifest_at is not canonical UTC seconds") from exc
    if _parse_utc(manifest_at) < _parse_utc(decision.decision_at):
        raise RealAssetRightsManifestV24Error(
            "manifest_at cannot predate the qualification decision"
        )
    if evidence.valid_until != "PERPETUAL" and _parse_utc(manifest_at) >= _parse_utc(
        evidence.valid_until
    ):
        raise RealAssetRightsManifestV24Error(
            "rights evidence expired before the exclusive manifest boundary"
        )

    pack_sha256 = _sha256(_canonical_document(pack))
    evidence_sha256 = _sha256(_canonical_document(evidence))
    review_a_sha256 = _sha256(_canonical_document(reviewer_a))
    review_b_sha256 = _sha256(_canonical_document(reviewer_b))
    pair_check_sha256 = _sha256(_canonical_document(pair_check))
    request_sha256 = _sha256(_canonical_document(request))
    instruction_sha256 = _sha256(_canonical_document(instruction))
    decision_sha256 = _sha256(_canonical_document(decision))
    _assert_pack_record_non_aliasing(
        pack=pack,
        closure_digests={
            pack_sha256,
            evidence_sha256,
            review_a_sha256,
            review_b_sha256,
            pair_check_sha256,
            request_sha256,
            instruction_sha256,
            decision_sha256,
            RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
            decision.policy_document_sha256,
            decision.evidence_retained_record_sha256,
            decision.evidence_preparer_ref_sha256,
            request.review_a_record_sha256,
            decision.reviewer_a_retained_record_sha256,
            request.review_b_record_sha256,
            decision.reviewer_b_retained_record_sha256,
            decision.qualifier_ref_sha256,
        },
    )

    payload: dict[str, object] = {
        "schema_version": "2.4.0",
        "document_type": "sdc.creative-sample-real-asset-rights-manifest-v2",
        "profile": RIGHTS_MANIFEST_V2_PROFILE,
        "manifest_at": manifest_at,
        "manifest_policy_id": RIGHTS_MANIFEST_V2_POLICY_ID,
        "manifest_policy_version": RIGHTS_MANIFEST_V2_POLICY_VERSION,
        "manifest_policy_document_sha256": RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256,
        "pack_id": pack.pack_id,
        "pack_manifest_sha256": pack_sha256,
        "rights_evidence_bundle_id": evidence.bundle_id,
        "rights_evidence_bundle_sha256": evidence_sha256,
        "review_a_id": reviewer_a.review_id,
        "review_a_contract_sha256": review_a_sha256,
        "review_b_id": reviewer_b.review_id,
        "review_b_contract_sha256": review_b_sha256,
        "pair_check_id": pair_check.pair_check_id,
        "pair_check_sha256": pair_check_sha256,
        "request_id": request.request_id,
        "request_sha256": request_sha256,
        "instruction_id": instruction.instruction_id,
        "instruction_sha256": instruction_sha256,
        "decision_id": decision.decision_id,
        "decision_sha256": decision_sha256,
        "qualification_policy_id": decision.policy_id,
        "qualification_policy_version": decision.policy_version,
        "qualification_policy_document_sha256": decision.policy_document_sha256,
        "evidence_valid_until": evidence.valid_until,
        "evidence_retained_record_sha256": decision.evidence_retained_record_sha256,
        "evidence_preparer_ref_sha256": decision.evidence_preparer_ref_sha256,
        "review_a_record_sha256": request.review_a_record_sha256,
        "reviewer_a_retained_record_sha256": decision.reviewer_a_retained_record_sha256,
        "review_b_record_sha256": request.review_b_record_sha256,
        "reviewer_b_retained_record_sha256": decision.reviewer_b_retained_record_sha256,
        "qualifier_ref_sha256": decision.qualifier_ref_sha256,
        "qualifier_record_sha256": decision.qualifier_record_sha256,
        "decision_at": decision.decision_at,
        "qualification_decision": decision.decision,
        "qualification_scope": decision.qualification_scope,
        "eligible_for_separate_manifest_design_review": True,
        "status": "RIGHTS_MANIFEST_CREATED",
        "rights_qualification_performed": True,
        "rights_manifest_created": True,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    try:
        return CreativeSampleRealAssetRightsManifestV2.model_validate(
            {
                "manifest_id": stable_id("real_asset_rights_manifest_v2", payload),
                **payload,
            },
            strict=True,
        )
    except ValidationError as exc:
        raise RealAssetRightsManifestV24Error(
            "rights manifest could not be built from the exact v2 closure"
        ) from exc


def verify_real_asset_rights_manifest_closure_v2(
    *,
    pack: CreativeSampleFrozenRealAssetPackManifest,
    evidence: CreativeSampleRealAssetRightsEvidenceBundleV2,
    reviewer_a: CreativeSampleRealAssetHumanPackReviewV2,
    reviewer_b: CreativeSampleRealAssetHumanPackReviewV2,
    pair_check: CreativeSampleRealAssetReviewPairCheckV2,
    request: CreativeSampleRealAssetQualificationRequestV2,
    instruction: CreativeSampleRealAssetQualificationDecisionInstructionV22,
    decision: CreativeSampleRealAssetQualificationDecisionV2,
    manifest: CreativeSampleRealAssetRightsManifestV2,
) -> CreativeSampleRealAssetRightsManifestV2:
    """Historically rebuild and verify an exact manifest without reading current time."""

    manifest = _revalidate(
        manifest,
        CreativeSampleRealAssetRightsManifestV2,
        field="rights manifest",
    )
    rebuilt = build_real_asset_rights_manifest_v2(
        pack=pack,
        evidence=evidence,
        reviewer_a=reviewer_a,
        reviewer_b=reviewer_b,
        pair_check=pair_check,
        request=request,
        instruction=instruction,
        decision=decision,
        manifest_at=manifest.manifest_at,
    )
    if rebuilt != manifest:
        raise RealAssetRightsManifestV24Error(
            "rights manifest drifted from the exact qualification closure"
        )
    return manifest


def _reject_json_constant(value: str) -> None:
    raise RealAssetRightsManifestV24Error(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RealAssetRightsManifestV24Error(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def parse_real_asset_rights_manifest_v2_json(
    raw: bytes,
) -> CreativeSampleRealAssetRightsManifestV2:
    """Parse one bounded in-memory manifest while rejecting ambiguous JSON."""

    if type(raw) is not bytes or not raw or len(raw) > _JSON_LIMIT:
        raise RealAssetRightsManifestV24Error(
            "rights manifest JSON must be bounded non-empty bytes"
        )
    try:
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise RealAssetRightsManifestV24Error(
            "rights manifest JSON is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise RealAssetRightsManifestV24Error("rights manifest JSON must contain one object")
    try:
        return CreativeSampleRealAssetRightsManifestV2.model_validate_json(raw, strict=True)
    except ValidationError as exc:
        raise RealAssetRightsManifestV24Error(
            "rights manifest JSON violates its strict contract"
        ) from exc


__all__ = [
    "RIGHTS_MANIFEST_V2_POLICY_DOCUMENT_SHA256",
    "RIGHTS_MANIFEST_V2_POLICY_ID",
    "RIGHTS_MANIFEST_V2_POLICY_VERSION",
    "RIGHTS_MANIFEST_V2_PROFILE",
    "CreativeSampleRealAssetRightsManifestV2",
    "RealAssetRightsManifestV24Error",
    "build_real_asset_rights_manifest_v2",
    "parse_real_asset_rights_manifest_v2_json",
    "verify_real_asset_rights_manifest_closure_v2",
]
