from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import zlib
from dataclasses import dataclass
from pathlib import Path, PosixPath, WindowsPath
from typing import Any

import pytest
from pydantic import ValidationError

import sdc.generated_reference_candidate as generated_reference_candidate
from sdc.contracts import (
    CanaryExecution,
    CanaryPlan,
    CharacterAssetVersion,
    CharacterBible,
    EvidenceBoundCanaryPlan,
    GenerationJob,
    InputMaterial,
    JobGraph,
    ProviderRequest,
    SceneAssetVersion,
    SceneBible,
)
from sdc.generated_reference_candidate import (
    EVIDENCE_CATEGORY_ORDER,
    GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
    GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
    GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
    GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
    GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
    GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
    GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256,
    QUALIFICATION_GATE_ORDER,
    QUALIFICATION_ISSUE_CODE_ORDER,
    CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    CreativeSampleGeneratedReferenceCandidateV1,
    CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    GeneratedReferenceCandidateError,
    GeneratedReferenceOutputDescriptorV1,
    GeneratedReferenceQualificationEvidenceInput,
    GeneratedReferenceQualificationEvidenceReferenceV1,
    GeneratedReferenceQualificationGateResultV1,
    admit_generated_reference_png,
    build_generated_reference_provider_attempt_outcome,
    capture_generated_reference_candidate,
    creative_sample_generated_reference_candidate_projection,
    creative_sample_generated_reference_candidate_qualification_decision_projection,
    creative_sample_generated_reference_candidate_qualification_decision_sha256,
    creative_sample_generated_reference_candidate_qualification_request_projection,
    creative_sample_generated_reference_candidate_qualification_request_sha256,
    creative_sample_generated_reference_candidate_sha256,
    creative_sample_generated_reference_provider_attempt_outcome_projection,
    creative_sample_generated_reference_provider_attempt_outcome_sha256,
    generated_reference_png_technical_record_projection,
    generated_reference_png_technical_record_sha256,
    generated_reference_provider_output_set_projection,
    generated_reference_provider_output_set_sha256,
    prepare_generated_reference_candidate_qualification_request,
    record_generated_reference_candidate_qualification_decision,
)
from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptArtifactV1,
    CreativeSampleReferenceVisualPromptCompileRequestV1,
    compile_creative_sample_reference_visual_prompt,
    creative_sample_reference_visual_prompt_artifact_projection,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PACKET = (
    ROOT
    / "tests/fixtures/visual_prompt_profiles/reference-compiler"
    / "reviewed-known-answer-source-v1.json"
)

ZERO_AUTHORITY = {
    "authority_scope": "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY",
    "current_gate": "HUMAN_GATE",
    "provider_state": "NOT_AUTHORIZED",
    "generation_authorized": False,
    "execution_authorized": False,
    "publication_authorized": False,
    "remote_processing_allowed": False,
    "retention_allowed": False,
    "training_allowed": False,
    "publication_allowed": False,
    "automated_execution_allowed": False,
    "authorized_attempts": 0,
    "authorized_cost_cny": 0,
    "posts_allowed": 0,
    "provider_requests": 0,
    "grants_rights": False,
    "grants_qualification": False,
    "grants_execution_authority": False,
    "eligible_for_asset_promotion": False,
    "replaces_rights_manifest": False,
    "usage_restriction": "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION",
}

GATE_EVIDENCE_CATEGORIES = {
    "PROVENANCE_CLOSURE": EVIDENCE_CATEGORY_ORDER,
    "PROMPT_AND_RECEIPT_CLOSURE": (),
    "OUTPUT_SET_COMPLETENESS": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "PROVIDER_TERMINAL_OBSERVATION",
    ),
    "TECHNICAL_MEDIA_FIT": (),
    "SUBJECT_AND_ASSET_PURPOSE_MATCH": ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    "IDENTITY_CONTINUITY": (
        "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
        "LIKENESS_PRIVACY_AND_SENSITIVE_DATA",
    ),
    "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION": ("INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",),
    "PROVIDER_GENERATION_PROVENANCE": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "PROVIDER_TERMINAL_OBSERVATION",
    ),
    "PROVIDER_OUTPUT_TERMS": ("PROVIDER_TERMS_AT_SUBMISSION",),
    "COPYRIGHT_AND_COMMERCIAL_SCOPE": ("OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",),
    "LIKENESS_PRIVACY_AND_SENSITIVE_DATA": ("LIKENESS_PRIVACY_AND_SENSITIVE_DATA",),
    "BRAND_AND_PROTECTED_CONTENT": ("BRAND_AND_PROTECTED_CONTENT",),
    "REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION": (
        "PROVIDER_ATTEMPT_PROVENANCE",
        "REMOTE_PROCESSING_AUTHORIZATION_AT_SUBMISSION",
    ),
    "RETENTION_POLICY_ALIGNMENT": (
        "PROVIDER_TERMS_AT_SUBMISSION",
        "RETENTION_POLICY_AT_SUBMISSION",
    ),
    "TRAINING_USE_POLICY_ALIGNMENT": (
        "PROVIDER_TERMS_AT_SUBMISSION",
        "TRAINING_USE_POLICY_AT_SUBMISSION",
    ),
}


def _canonical_document(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _canonical_compact(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _domain_sha256(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + _canonical_compact(value)).hexdigest()


def _semantic_leaf_paths(value: object, path: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    if type(value) is dict:
        result: list[tuple[object, ...]] = []
        for key, nested in value.items():
            result.extend(_semantic_leaf_paths(nested, (*path, key)))
        return result
    if type(value) is list:
        if not value:
            return [path]
        result = []
        for index, nested in enumerate(value):
            result.extend(_semantic_leaf_paths(nested, (*path, index)))
        return result
    return [path]


def _mutate_semantic_leaf(value: object, path: tuple[object, ...]) -> object:
    changed = copy.deepcopy(value)
    parent = changed
    for component in path[:-1]:
        parent = parent[component]  # type: ignore[index]
    final = path[-1]
    original = parent[final]  # type: ignore[index]
    if original is None:
        replacement: object = "MUTATED"
    elif type(original) is bool:
        replacement = not original
    elif type(original) is int:
        replacement = original + 1
    elif type(original) is str:
        replacement = f"{original}~"
    elif type(original) is list and not original:
        replacement = ["MUTATED"]
    else:
        raise AssertionError(f"unhandled semantic leaf at {path!r}")
    parent[final] = replacement  # type: ignore[index]
    return changed


def _chunk(name: bytes, payload: bytes) -> bytes:
    return (
        len(payload).to_bytes(4, "big")
        + name
        + payload
        + (zlib.crc32(name + payload) & 0xFFFFFFFF).to_bytes(4, "big")
    )


def _png_ihdr(
    *,
    width: int = 512,
    height: int = 512,
    rgba: bool = False,
    interlace: int = 0,
) -> bytes:
    return (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes((8, 6 if rgba else 2, 0, 0, interlace))
    )


def _png_document(chunks: tuple[tuple[bytes, bytes], ...]) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"".join(_chunk(name, payload) for name, payload in chunks)


def _standard_png_chunk_payload(name: bytes) -> bytes:
    payloads = {
        b"cHRM": b"".join(
            value.to_bytes(4, "big")
            for value in (31_270, 32_900, 64_000, 33_000, 30_000, 60_000, 15_000, 6_000)
        ),
        b"gAMA": (45_455).to_bytes(4, "big"),
        b"iCCP": b"profile\x00\x00" + zlib.compress(b"synthetic-icc-profile"),
        b"sBIT": b"\x08\x08\x08",
        b"sRGB": b"\x00",
        b"PLTE": b"\x00\x00\x00",
        b"bKGD": b"\x00\x00\x00\x00\x00\x00",
        b"hIST": b"\x00\x01",
        b"pHYs": (2_835).to_bytes(4, "big") * 2 + b"\x01",
        b"tEXt": b"purpose\x00synthetic known answer",
        b"tIME": (2026).to_bytes(2, "big") + bytes((8, 29, 1, 3, 0)),
    }
    return payloads[name]


def _synthetic_png(
    *,
    width: int = 512,
    height: int = 512,
    rgba: bool = False,
    alpha: int = 255,
    metadata_chunks: tuple[tuple[bytes, bytes], ...] = (),
) -> bytes:
    pixel = bytes((0x11, 0x22, 0x33, alpha)) if rgba else b"\x11\x22\x33"
    scanline = b"\x00" + pixel * width
    raw = scanline * height
    return _png_document(
        (
            (b"IHDR", _png_ihdr(width=width, height=height, rgba=rgba)),
            *metadata_chunks,
            (b"IDAT", zlib.compress(raw, level=9)),
            (b"IEND", b""),
        )
    )


def _invalid_png(case: str) -> bytes:
    ihdr = _png_ihdr()
    scanlines = (b"\x00" + b"\x11\x22\x33" * 512) * 512
    compressed = zlib.compress(scanlines, level=9)
    if case == "signature":
        return b"not-png!" + _chunk(b"IHDR", ihdr)
    if case == "declared_length":
        return b"\x89PNG\r\n\x1a\n" + (2**32 - 1).to_bytes(4, "big") + b"IHDR"
    if case == "crc":
        damaged_ihdr = bytearray(_chunk(b"IHDR", ihdr))
        damaged_ihdr[-1] ^= 1
        return (
            b"\x89PNG\r\n\x1a\n"
            + bytes(damaged_ihdr)
            + _chunk(b"IDAT", compressed)
            + _chunk(b"IEND", b"")
        )
    if case == "nonconsecutive_idat":
        return _png_document(
            (
                (b"IHDR", ihdr),
                (b"IDAT", compressed),
                (b"vpAg", b"metadata"),
                (b"IDAT", b""),
                (b"IEND", b""),
            )
        )
    if case == "idat_count":
        return _png_document(((b"IHDR", ihdr), *((b"IDAT", b""),) * 513, (b"IEND", b"")))
    if case == "ancillary_count":
        return _png_document(
            (
                (b"IHDR", ihdr),
                *((b"vpAg", b""),) * 65,
                (b"IDAT", compressed),
                (b"IEND", b""),
            )
        )
    if case == "ancillary_payload":
        return _png_document(
            (
                (b"IHDR", ihdr),
                (b"vpAg", b"x" * 1_048_577),
                (b"IDAT", compressed),
                (b"IEND", b""),
            )
        )
    if case == "metadata_type_count":
        metadata = tuple(
            (bytes((0x61, 0x61 + index // 26, 0x41, 0x61 + index % 26)), b"") for index in range(33)
        )
        return _png_document(((b"IHDR", ihdr), *metadata, (b"IDAT", compressed), (b"IEND", b"")))
    if case == "trns":
        extra = (b"tRNS", b"\x00" * 6)
    elif case in {"actl", "fctl", "fdat"}:
        extra = ({"actl": b"acTL", "fctl": b"fcTL", "fdat": b"fdAT"}[case], b"\x00" * 8)
    elif case == "unknown_critical":
        extra = (b"ABCD", b"")
    else:
        extra = (b"vpAg", b"")
    if case == "interlace":
        ihdr = _png_ihdr(interlace=1)
    elif case == "bit_depth":
        ihdr = ihdr[:8] + bytes((16, 2, 0, 0, 0))
    elif case == "color_type":
        ihdr = ihdr[:8] + bytes((8, 3, 0, 0, 0))
    elif case == "dimensions":
        ihdr = _png_ihdr(width=511)
    if case == "invalid_zlib":
        compressed = b"not-a-zlib-stream"
    elif case == "decompressed_overflow":
        compressed = zlib.compress(scanlines + b"\x00", level=9)
    elif case == "scanline_filter":
        compressed = zlib.compress(b"\x05" + scanlines[1:], level=9)
    return _png_document(
        (
            (b"IHDR", ihdr),
            *((extra,) if case in {"trns", "actl", "fctl", "fdat", "unknown_critical"} else ()),
            (b"IDAT", compressed),
            (b"IEND", b""),
        )
    )


def _artifact(case_index: int = 0) -> CreativeSampleReferenceVisualPromptArtifactV1:
    packet = json.loads(SOURCE_PACKET.read_bytes())
    case = packet["cases"][case_index]
    request = CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
        _canonical_compact(case["request"])
    )
    if case["request"]["asset_purpose"] == "CHARACTER_REFERENCE_ASSET":
        subject = CharacterBible.model_validate(case["subject"])
    else:
        subject = SceneBible.model_validate(case["subject"])
    return compile_creative_sample_reference_visual_prompt(subject, request)


def _human_reference(identity_ref: str) -> bytes:
    return _canonical_document(
        {
            "document_profile": "sdc.privacy-minimized-human-reference.v1",
            "identity_namespace": "synthetic-reviewers",
            "identity_ref": identity_ref,
        }
    )


def _evidence_documents() -> tuple[GeneratedReferenceQualificationEvidenceInput, ...]:
    result = []
    for index, category in enumerate(EVIDENCE_CATEGORY_ORDER):
        record_id = (
            "synthetic-provider-terms"
            if category == "PROVIDER_TERMS_AT_SUBMISSION"
            else (f"synthetic-evidence-{index:02d}")
        )
        payload = {
            "category": category,
            "record_id": record_id,
            "document_profile": "sdc.synthetic-evidence.v1",
            "observed_at": "2026-08-29T00:00:00Z",
            "effective_from": "2026-08-28T00:00:00Z",
            "effective_until": "2026-08-30T00:00:00Z",
            "evidence_valid_until": "2026-08-30T00:00:00Z",
            "synthetic_known_answer": f"reviewed-{index:02d}",
        }
        raw = _canonical_document(payload)
        reference = GeneratedReferenceQualificationEvidenceReferenceV1.model_validate(
            {
                "category": category,
                "record_id": record_id,
                "document_profile": "sdc.synthetic-evidence.v1",
                "media_type": "application/json",
                "document_size_bytes": len(raw),
                "document_sha256": hashlib.sha256(raw).hexdigest(),
                "observed_at": payload["observed_at"],
                "effective_from": payload["effective_from"],
                "effective_until": payload["effective_until"],
                "evidence_valid_until": payload["evidence_valid_until"],
            }
        )
        result.append(
            GeneratedReferenceQualificationEvidenceInput(
                reference=reference,
                document_bytes=raw,
            )
        )
    return tuple(result)


def _mutated_evidence_documents(
    evidence: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    category: str,
    **updates: object,
) -> tuple[GeneratedReferenceQualificationEvidenceInput, ...]:
    result = list(evidence)
    index = EVIDENCE_CATEGORY_ORDER.index(category)  # type: ignore[arg-type]
    original = result[index]
    document = json.loads(original.document_bytes)
    document.update(updates)
    raw = _canonical_document(document)
    reference_updates = {
        key: value
        for key, value in updates.items()
        if key
        in {
            "record_id",
            "document_profile",
            "observed_at",
            "effective_from",
            "effective_until",
            "evidence_valid_until",
        }
    }
    reference = GeneratedReferenceQualificationEvidenceReferenceV1.model_validate(
        {
            **original.reference.model_dump(mode="python"),
            **reference_updates,
            "document_size_bytes": len(raw),
            "document_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    result[index] = GeneratedReferenceQualificationEvidenceInput(
        reference=reference,
        document_bytes=raw,
    )
    return tuple(result)


def _bind_output_set_sha256(projection: dict[str, object]) -> dict[str, object]:
    descriptors = projection["output_descriptors"]
    assert type(descriptors) in {list, tuple}
    descriptor_documents = [
        item.model_dump(mode="json") if type(item) is GeneratedReferenceOutputDescriptorV1 else item
        for item in descriptors
    ]
    output_set_projection = {
        "expected_output_count": projection["expected_output_count"],
        "reported_output_count_bounded": projection["reported_output_count_bounded"],
        "reported_output_count_overflow": projection["reported_output_count_overflow"],
        "verified_output_count": projection["verified_output_count"],
        "output_descriptors": descriptor_documents,
    }
    projection["output_set_sha256"] = _domain_sha256(
        GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
        output_set_projection,
    )
    return projection


def _numeric_boolean_leaf_paths(
    value: object,
    path: tuple[str | int, ...] = (),
) -> tuple[tuple[str | int, ...], ...]:
    if type(value) in {bool, int}:
        return (path,)
    if type(value) is dict:
        return tuple(
            nested_path
            for key, nested in value.items()
            for nested_path in _numeric_boolean_leaf_paths(nested, (*path, key))
        )
    if type(value) in {list, tuple}:
        return tuple(
            nested_path
            for index, nested in enumerate(value)
            for nested_path in _numeric_boolean_leaf_paths(nested, (*path, index))
        )
    return ()


def _replace_tree_leaf(
    value: object,
    path: tuple[str | int, ...],
    replacement: object,
) -> object:
    if not path:
        return replacement
    head, *tail = path
    remaining = tuple(tail)
    if type(value) is dict and type(head) is str:
        result = dict(value)
        result[head] = _replace_tree_leaf(result[head], remaining, replacement)
        return result
    if type(value) is list and type(head) is int:
        result_list = list(value)
        result_list[head] = _replace_tree_leaf(result_list[head], remaining, replacement)
        return result_list
    if type(value) is tuple and type(head) is int:
        result_tuple = list(value)
        result_tuple[head] = _replace_tree_leaf(result_tuple[head], remaining, replacement)
        return tuple(result_tuple)
    raise AssertionError(f"invalid test tree path: {path!r}")


def _tree_leaf(value: object, path: tuple[str | int, ...]) -> object:
    current = value
    for part in path:
        if type(current) is dict and type(part) is str:
            current = current[part]
        elif type(current) in {list, tuple} and type(part) is int:
            current = current[part]
        else:
            raise AssertionError(f"invalid test tree path: {path!r}")
    return current


def _path_name(path: tuple[str | int, ...]) -> str:
    return ".".join(str(part) for part in path)


def _outcome(
    artifact: CreativeSampleReferenceVisualPromptArtifactV1,
    descriptor: GeneratedReferenceOutputDescriptorV1,
    evidence: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
) -> CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1:
    projection = creative_sample_reference_visual_prompt_artifact_projection(artifact)
    snapshot = projection["profile_snapshot"]
    receipt = projection["prompt_render_receipt"]
    assert isinstance(snapshot, dict) and isinstance(receipt, dict)
    evidence_by_category = {item.reference.category: item.reference for item in evidence}
    outcome_projection: dict[str, object] = {
        "schema_version": "1.0.0",
        "document_type": ("sdc.creative-sample-generated-reference-provider-attempt-outcome-v1"),
        "outcome_purpose": ("CALLER_ASSERTED_IMMUTABLE_PROVIDER_ATTEMPT_OUTCOME_EVIDENCE_ONLY"),
        "reference_prompt_artifact_sha256": artifact.artifact_sha256,
        "asset_purpose": projection["asset_purpose"],
        "subject_id": projection["subject_id"],
        "expected_active_asset_version_id": projection["expected_active_asset_version_id"],
        "expected_active_asset_content_sha256": projection["expected_active_asset_content_sha256"],
        "profile_id": snapshot["profile_id"],
        "profile_version": snapshot["profile_version"],
        "profile_sha256": snapshot["profile_sha256"],
        "catalog_version": snapshot["catalog_version"],
        "catalog_sha256": snapshot["catalog_sha256"],
        "render_input_sha256": projection["render_input_sha256"],
        "submitted_prompt_sha256": projection["prompt_sha256"],
        "submitted_prompt_size_bytes": projection["prompt_size_bytes"],
        "prompt_render_receipt_sha256": receipt["prompt_render_receipt_sha256"],
        "provider": "synthetic-provider",
        "model": "synthetic-model",
        "provider_region": "synthetic-region",
        "provider_terms_snapshot_id": "synthetic-provider-terms",
        "provider_terms_snapshot_sha256": evidence_by_category[
            "PROVIDER_TERMS_AT_SUBMISSION"
        ].document_sha256,
        "provider_terms_observed_at": "2026-08-29T00:00:00Z",
        "provider_terms_valid_from": "2026-08-28T00:00:00Z",
        "provider_terms_valid_until": "2026-08-30T00:00:00Z",
        "attempt_provenance_record_sha256": evidence_by_category[
            "PROVIDER_ATTEMPT_PROVENANCE"
        ].document_sha256,
        "terminal_observation_record_sha256": evidence_by_category[
            "PROVIDER_TERMINAL_OBSERVATION"
        ].document_sha256,
        "historical_execution_authorization_status": "CLAIMED_PRESENT",
        "attempt_ordinal": 1,
        "submitted_input_material_count": 0,
        "submitted_at": "2026-08-29T01:00:00Z",
        "terminal_observed_at": "2026-08-29T01:01:00Z",
        "terminal_disposition": "VERIFIED_SUCCESS",
        "terminal_reason_code": None,
        "provider_task_reference_status": "PRESENT_IN_RETAINED_RECORD",
        "expected_output_count": 1,
        "reported_output_count_bounded": 1,
        "reported_output_count_overflow": False,
        "verified_output_count": 1,
        "output_descriptors": (descriptor,),
        "observed_provider_request_count": 1,
        **ZERO_AUTHORITY,
    }
    return build_generated_reference_provider_attempt_outcome(
        _bind_output_set_sha256(outcome_projection)
    )


def _preparer_action(
    candidate: CreativeSampleGeneratedReferenceCandidateV1,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
    evidence: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
    preparer_reference: bytes,
) -> bytes:
    return _canonical_document(
        {
            "document_profile": (
                "sdc.generated-reference-qualification-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_QUALIFICATION_EVIDENCE",
            "actor_ref_sha256": hashlib.sha256(preparer_reference).hexdigest(),
            "candidate_sha256": candidate.candidate_sha256,
            "provider_attempt_outcome_sha256": outcome.outcome_sha256,
            "policy_document_sha256": (GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256),
            "requested_at": "2026-08-29T01:02:00Z",
            "evidence_document_sha256s": [item.reference.document_sha256 for item in evidence],
        }
    )


def _gate_results(
    evidence: tuple[GeneratedReferenceQualificationEvidenceInput, ...],
) -> tuple[GeneratedReferenceQualificationGateResultV1, ...]:
    ids = {item.reference.category: item.reference.record_id for item in evidence}
    return tuple(
        GeneratedReferenceQualificationGateResultV1.model_validate(
            {
                "gate": gate,
                "result": "PASS",
                "evidence_record_ids": tuple(
                    ids[category] for category in GATE_EVIDENCE_CATEGORIES[gate]
                ),
                "basis": "Synthetic first-party human known-answer PASS.",
            }
        )
        for gate in QUALIFICATION_GATE_ORDER
    )


def _qualifier_action(
    request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    gates: tuple[GeneratedReferenceQualificationGateResultV1, ...],
    qualifier_reference: bytes,
    *,
    issue_codes: tuple[str, ...] = (),
    decision: str = "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
    eligible: bool = True,
    decision_at: str = "2026-08-29T01:03:00Z",
) -> bytes:
    return _canonical_document(
        {
            "document_profile": "sdc.generated-reference-qualification-decision-action.v1",
            "action": "RECORDED_GENERATED_REFERENCE_QUALIFICATION_DECISION",
            "actor_ref_sha256": hashlib.sha256(qualifier_reference).hexdigest(),
            "request_sha256": request.request_sha256,
            "decision_at": decision_at,
            "gate_results": [item.model_dump(mode="json") for item in gates],
            "qualification_issue_codes": list(issue_codes),
            "qualification_basis": "Synthetic independent human qualification closure.",
            "decision": decision,
            "eligible_for_separate_generated_rights_manifest_review": eligible,
        }
    )


@dataclass(frozen=True)
class Closure:
    artifact: CreativeSampleReferenceVisualPromptArtifactV1
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1
    candidate: CreativeSampleGeneratedReferenceCandidateV1
    request: CreativeSampleGeneratedReferenceCandidateQualificationRequestV1
    decision: CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1
    evidence: tuple[GeneratedReferenceQualificationEvidenceInput, ...]
    preparer_reference: bytes
    preparer_action: bytes
    qualifier_reference: bytes
    qualifier_action: bytes
    png_path: Path


def _closure(tmp_path: Path, *, case_index: int = 0) -> Closure:
    png_path = tmp_path / "synthetic-reference.png"
    png_path.write_bytes(_synthetic_png(rgba=case_index != 0))
    descriptor = admit_generated_reference_png(png_path)
    evidence = _evidence_documents()
    artifact = _artifact(case_index)
    outcome = _outcome(artifact, descriptor, evidence)
    candidate = capture_generated_reference_candidate(artifact, outcome, png_path=png_path)
    preparer_reference = _human_reference("preparer-001")
    preparer_action = _preparer_action(candidate, outcome, evidence, preparer_reference)
    request = prepare_generated_reference_candidate_qualification_request(
        artifact,
        outcome,
        candidate,
        png_path=png_path,
        evidence_documents=evidence,
        preparer_reference_bytes=preparer_reference,
        preparer_action_bytes=preparer_action,
        requested_at="2026-08-29T01:02:00Z",
    )
    gates = _gate_results(evidence)
    qualifier_reference = _human_reference("qualifier-001")
    qualifier_action = _qualifier_action(request, gates, qualifier_reference)
    decision = record_generated_reference_candidate_qualification_decision(
        artifact,
        outcome,
        candidate,
        request,
        png_path=png_path,
        evidence_documents=evidence,
        preparer_reference_bytes=preparer_reference,
        preparer_action_bytes=preparer_action,
        qualifier_reference_bytes=qualifier_reference,
        qualifier_action_bytes=qualifier_action,
        decision_at="2026-08-29T01:03:00Z",
        gate_results=gates,
        qualification_issue_codes=(),
        qualification_basis="Synthetic independent human qualification closure.",
        decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
    )
    return Closure(
        artifact=artifact,
        outcome=outcome,
        candidate=candidate,
        request=request,
        decision=decision,
        evidence=evidence,
        preparer_reference=preparer_reference,
        preparer_action=preparer_action,
        qualifier_reference=qualifier_reference,
        qualifier_action=qualifier_action,
        png_path=png_path,
    )


def _prepare_changed_outcome(
    closure: Closure,
    outcome: CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
) -> tuple[
    CreativeSampleGeneratedReferenceCandidateV1,
    CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
    bytes,
]:
    candidate = capture_generated_reference_candidate(
        closure.artifact,
        outcome,
        png_path=closure.png_path,
    )
    preparer_action = _preparer_action(
        candidate,
        outcome,
        closure.evidence,
        closure.preparer_reference,
    )
    request = prepare_generated_reference_candidate_qualification_request(
        closure.artifact,
        outcome,
        candidate,
        png_path=closure.png_path,
        evidence_documents=closure.evidence,
        preparer_reference_bytes=closure.preparer_reference,
        preparer_action_bytes=preparer_action,
        requested_at="2026-08-29T01:02:00Z",
    )
    return candidate, request, preparer_action


def _formal_digest_aliases(
    closure: Closure,
    *,
    include_request: bool,
) -> dict[str, str]:
    result = {
        "evidence_document": closure.evidence[0].reference.document_sha256,
        "policy_document": GENERATED_REFERENCE_QUALIFICATION_POLICY_DOCUMENT_SHA256,
        "artifact_domain": closure.artifact.artifact_sha256,
        "outcome_domain": closure.outcome.outcome_sha256,
        "candidate_domain": closure.candidate.candidate_sha256,
        "output_set_domain": closure.outcome.output_set_sha256,
        "png_technical_record_domain": closure.candidate.media_technical_record_sha256,
        "png_content_raw": closure.candidate.media_content_sha256,
        "profile_nested": closure.candidate.profile_sha256,
        "catalog_nested": closure.candidate.catalog_sha256,
        "render_input_nested": closure.candidate.render_input_sha256,
        "prompt_receipt_nested": closure.candidate.prompt_render_receipt_sha256,
    }
    if include_request:
        result["request_domain"] = closure.request.request_sha256
    return result


@pytest.mark.parametrize("case_index", [0, 2])
def test_complete_character_and_scene_closure_is_deterministic(
    tmp_path: Path,
    case_index: int,
) -> None:
    closure = _closure(tmp_path, case_index=case_index)

    pairs: tuple[tuple[Any, Any, bytes], ...] = (
        (
            closure.outcome,
            creative_sample_generated_reference_provider_attempt_outcome_projection,
            GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
        ),
        (
            closure.candidate,
            creative_sample_generated_reference_candidate_projection,
            GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
        ),
        (
            closure.request,
            creative_sample_generated_reference_candidate_qualification_request_projection,
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
        ),
        (
            closure.decision,
            creative_sample_generated_reference_candidate_qualification_decision_projection,
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
        ),
    )
    for value, projection_function, domain in pairs:
        projection = projection_function(value)
        digest_field = next(
            field
            for field in type(value).model_fields
            if field.endswith("_sha256")
            and field.split("_")[0] in {"outcome", "candidate", "request", "decision"}
        )
        assert getattr(value, digest_field) == _domain_sha256(domain, projection)

    assert creative_sample_generated_reference_provider_attempt_outcome_sha256(closure.outcome) == (
        closure.outcome.outcome_sha256
    )
    assert creative_sample_generated_reference_candidate_sha256(closure.candidate) == (
        closure.candidate.candidate_sha256
    )
    assert (
        creative_sample_generated_reference_candidate_qualification_request_sha256(closure.request)
        == closure.request.request_sha256
    )
    assert (
        creative_sample_generated_reference_candidate_qualification_decision_sha256(
            closure.decision
        )
        == closure.decision.decision_sha256
    )
    assert closure.decision.decision == "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
    assert closure.decision.eligible_for_separate_generated_rights_manifest_review is True
    assert closure.request.request_valid_until == "2026-08-30T00:00:00Z"
    assert closure.decision.qualification_valid_until == "2026-08-30T00:00:00Z"


def test_png_and_output_set_domains_are_explicit(tmp_path: Path) -> None:
    png_path = tmp_path / "reference.png"
    png_path.write_bytes(_synthetic_png(rgba=True))
    descriptor = admit_generated_reference_png(png_path)
    record_projection = generated_reference_png_technical_record_projection(
        descriptor.technical_record
    )
    assert descriptor.technical_record_sha256 == _domain_sha256(
        GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
        record_projection,
    )
    assert generated_reference_png_technical_record_sha256(descriptor.technical_record) == (
        descriptor.technical_record_sha256
    )

    artifact = _artifact()
    evidence = _evidence_documents()
    outcome = _outcome(artifact, descriptor, evidence)
    output_projection = generated_reference_provider_output_set_projection(outcome)
    assert outcome.output_set_sha256 == _domain_sha256(
        GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
        output_projection,
    )
    assert generated_reference_provider_output_set_sha256(outcome) == outcome.output_set_sha256


def test_every_semantic_leaf_changes_its_domain_digest_and_self_fields_are_excluded(
    tmp_path: Path,
) -> None:
    closure = _closure(tmp_path)
    png_record = closure.outcome.output_descriptors[0].technical_record
    projections = (
        (
            generated_reference_png_technical_record_projection(png_record),
            GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
        ),
        (
            generated_reference_provider_output_set_projection(closure.outcome),
            GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
        ),
        (
            creative_sample_generated_reference_provider_attempt_outcome_projection(
                closure.outcome
            ),
            GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
        ),
        (
            creative_sample_generated_reference_candidate_projection(closure.candidate),
            GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
        ),
        (
            creative_sample_generated_reference_candidate_qualification_request_projection(
                closure.request
            ),
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
        ),
        (
            creative_sample_generated_reference_candidate_qualification_decision_projection(
                closure.decision
            ),
            GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
        ),
    )
    for projection, domain in projections:
        baseline = _domain_sha256(domain, projection)
        paths = _semantic_leaf_paths(projection)
        assert paths
        for path in paths:
            assert _domain_sha256(domain, _mutate_semantic_leaf(projection, path)) != baseline

    assert "outcome_id" not in projections[2][0] and "outcome_sha256" not in projections[2][0]
    assert "candidate_id" not in projections[3][0] and "candidate_sha256" not in projections[3][0]
    assert "request_id" not in projections[4][0] and "request_sha256" not in projections[4][0]
    assert "decision_id" not in projections[5][0] and "decision_sha256" not in projections[5][0]


def test_domains_are_non_aliasing_and_prompt_media_hashes_remain_raw(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    common_projection = {"same": "semantic-projection"}
    domains = (
        GENERATED_REFERENCE_PNG_TECHNICAL_RECORD_SHA256_DOMAIN,
        GENERATED_REFERENCE_PROVIDER_OUTPUT_SET_SHA256_DOMAIN,
        GENERATED_REFERENCE_PROVIDER_ATTEMPT_OUTCOME_SHA256_DOMAIN,
        GENERATED_REFERENCE_CANDIDATE_SHA256_DOMAIN,
        GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_REQUEST_SHA256_DOMAIN,
        GENERATED_REFERENCE_CANDIDATE_QUALIFICATION_DECISION_SHA256_DOMAIN,
    )
    digests = {_domain_sha256(domain, common_projection) for domain in domains}
    assert len(digests) == len(domains)

    prompt_bytes = closure.artifact.prompt.encode("utf-8")
    media_bytes = closure.png_path.read_bytes()
    assert hashlib.sha256(prompt_bytes).hexdigest() == closure.artifact.prompt_sha256
    assert hashlib.sha256(media_bytes).hexdigest() == closure.candidate.media_content_sha256
    assert _domain_sha256(domains[0], closure.artifact.prompt) != closure.artifact.prompt_sha256
    assert _domain_sha256(domains[0], media_bytes.hex()) != closure.candidate.media_content_sha256


def test_models_are_strict_frozen_extra_forbid_and_zero_authority(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    for value in (closure.outcome, closure.candidate, closure.request, closure.decision):
        assert value.model_config["frozen"] is True
        assert value.model_config["strict"] is True
        assert value.model_config["extra"] == "forbid"
        projection = value.model_dump(mode="json")
        for field, expected in ZERO_AUTHORITY.items():
            assert projection[field] == expected
        with pytest.raises(ValidationError):
            type(value).model_validate({**projection, "unexpected": "rejected"})
        with pytest.raises(ValidationError):
            value.current_gate = "HUMAN_GATE"  # type: ignore[misc]


@pytest.mark.parametrize(
    "drift",
    [
        "artifact_identity",
        "profile",
        "render_input",
        "prompt_bytes",
        "prompt_receipt",
    ],
)
def test_candidate_capture_rejects_artifact_profile_prompt_receipt_drift(
    tmp_path: Path,
    drift: str,
) -> None:
    closure = _closure(tmp_path)
    artifact = closure.artifact
    if drift == "artifact_identity":
        changed = artifact.model_copy(update={"artifact_sha256": "0" * 64})
    elif drift == "profile":
        changed = artifact.model_copy(
            update={
                "profile_snapshot": artifact.profile_snapshot.model_copy(
                    update={"profile_sha256": "0" * 64}
                )
            }
        )
    elif drift == "render_input":
        changed = artifact.model_copy(update={"render_input_sha256": "0" * 64})
    elif drift == "prompt_bytes":
        changed = artifact.model_copy(update={"prompt": f"{artifact.prompt} drift"})
    else:
        changed = artifact.model_copy(
            update={
                "prompt_render_receipt": artifact.prompt_render_receipt.model_copy(
                    update={"prompt_sha256": "0" * 64}
                )
            }
        )
    with pytest.raises(GeneratedReferenceCandidateError):
        capture_generated_reference_candidate(
            changed,
            closure.outcome,
            png_path=closure.png_path,
        )


def test_png_admission_rejects_non_path_trailing_bytes_and_custom_subclass(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reference.png"
    path.write_bytes(_synthetic_png())
    assert admit_generated_reference_png(path).regular_file_verified is True
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(str(path))  # type: ignore[arg-type]
    path.write_bytes(_synthetic_png() + b"trailing")
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(path)

    class DangerousPath(type(tmp_path)):
        pass

    dangerous = DangerousPath(tmp_path / "reference.png")
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(dangerous)


def test_png_admission_accepts_the_native_windows_or_posix_path(tmp_path: Path) -> None:
    native_path_type = WindowsPath if os.name == "nt" else PosixPath
    foreign_path_type = PosixPath if os.name == "nt" else WindowsPath
    assert type(tmp_path) is native_path_type
    with pytest.raises(NotImplementedError):
        foreign_path_type("foreign-platform-path")

    path = tmp_path / "native.png"
    path.write_bytes(_synthetic_png())
    assert (
        admit_generated_reference_png(path).content_sha256
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_png_admission_rejects_directory_empty_oversize_and_symlink(tmp_path: Path) -> None:
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(tmp_path)

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(empty)

    oversized = tmp_path / "oversized.png"
    with oversized.open("wb") as handle:
        handle.seek(67_108_864)
        handle.write(b"\x00")
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(oversized)

    target = tmp_path / "target.png"
    target.write_bytes(_synthetic_png())
    linked = tmp_path / "linked.png"
    try:
        linked.symlink_to(target)
    except OSError:
        pass
    else:
        with pytest.raises(GeneratedReferenceCandidateError):
            admit_generated_reference_png(linked)


def test_png_admission_and_candidate_capture_reject_hardlinks(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    hardlink = tmp_path / "hardlinked-reference.png"
    try:
        hardlink.hardlink_to(closure.png_path)
    except OSError as exc:
        pytest.skip(f"filesystem does not support a local hardlink regression: {exc}")
    assert closure.png_path.stat().st_nlink == 2
    assert hardlink.stat().st_nlink == 2
    for path in (closure.png_path, hardlink):
        with pytest.raises(GeneratedReferenceCandidateError):
            admit_generated_reference_png(path)
    with pytest.raises(GeneratedReferenceCandidateError):
        capture_generated_reference_candidate(
            closure.artifact,
            closure.outcome,
            png_path=closure.png_path,
        )


def test_png_total_chunk_limit_is_dominated_by_tighter_frozen_subtype_limits() -> None:
    maximum_reachable_before_a_tighter_limit = 1 + 1 + 512 + 64 + 1
    assert maximum_reachable_before_a_tighter_limit == 579
    assert maximum_reachable_before_a_tighter_limit < 1_024


@pytest.mark.parametrize(
    "case",
    [
        "signature",
        "declared_length",
        "crc",
        "nonconsecutive_idat",
        "idat_count",
        "ancillary_count",
        "ancillary_payload",
        "metadata_type_count",
        "trns",
        "actl",
        "fctl",
        "fdat",
        "unknown_critical",
        "interlace",
        "bit_depth",
        "color_type",
        "dimensions",
        "invalid_zlib",
        "decompressed_overflow",
        "scanline_filter",
    ],
)
def test_png_parser_rejects_frozen_profile_violations(tmp_path: Path, case: str) -> None:
    path = tmp_path / f"invalid-{case}.png"
    path.write_bytes(_invalid_png(case))
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(path)


@pytest.mark.parametrize(
    ("chunk_name", "placement"),
    [
        *((name, "after_plte") for name in (b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB")),
        *((name, "after_idat") for name in (b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB")),
        (b"PLTE", "after_idat"),
        (b"bKGD", "before_plte"),
        (b"bKGD", "after_idat"),
        (b"hIST", "before_plte"),
        (b"hIST", "after_idat"),
        (b"pHYs", "after_idat"),
    ],
)
def test_png_parser_rejects_valid_crc_ancillary_chunk_misplacement(
    tmp_path: Path,
    chunk_name: bytes,
    placement: str,
) -> None:
    scanlines = (b"\x00" + b"\x11\x22\x33" * 512) * 512
    idat = (b"IDAT", zlib.compress(scanlines, level=9))
    ihdr = (b"IHDR", _png_ihdr())
    target = (chunk_name, _standard_png_chunk_payload(chunk_name))
    plte = (b"PLTE", _standard_png_chunk_payload(b"PLTE"))
    if placement == "after_plte":
        chunks = (ihdr, plte, target, idat, (b"IEND", b""))
    elif placement == "before_plte":
        chunks = (ihdr, target, plte, idat, (b"IEND", b""))
    else:
        chunks = (ihdr, idat, target, (b"IEND", b""))
    path = tmp_path / f"misplaced-{chunk_name.decode()}-{placement}.png"
    path.write_bytes(_png_document(chunks))
    with pytest.raises(GeneratedReferenceCandidateError):
        admit_generated_reference_png(path)


def test_png_parser_accepts_legal_metadata_placement_including_post_idat_text_time(
    tmp_path: Path,
) -> None:
    scanlines = (b"\x00" + b"\x11\x22\x33" * 512) * 512
    names = (b"cHRM", b"gAMA", b"sBIT", b"sRGB")
    before_plte = tuple((name, _standard_png_chunk_payload(name)) for name in names)
    after_plte = tuple(
        (name, _standard_png_chunk_payload(name)) for name in (b"bKGD", b"hIST", b"pHYs")
    )
    post_idat = tuple((name, _standard_png_chunk_payload(name)) for name in (b"tEXt", b"tIME"))
    path = tmp_path / "legal-metadata-order.png"
    path.write_bytes(
        _png_document(
            (
                (b"IHDR", _png_ihdr()),
                *before_plte,
                (b"PLTE", _standard_png_chunk_payload(b"PLTE")),
                *after_plte,
                (b"IDAT", zlib.compress(scanlines, level=9)),
                *post_idat,
                (b"IEND", b""),
            )
        )
    )
    record = admit_generated_reference_png(path).technical_record
    assert record.metadata_chunk_types == (
        "cHRM",
        "gAMA",
        "sBIT",
        "sRGB",
        "bKGD",
        "hIST",
        "pHYs",
        "tEXt",
        "tIME",
    )


def test_png_parser_records_alpha_and_unique_metadata_order(tmp_path: Path) -> None:
    opaque_path = tmp_path / "opaque.png"
    opaque_path.write_bytes(_synthetic_png(rgba=True))
    assert admit_generated_reference_png(opaque_path).technical_record.alpha_status == "OPAQUE"

    metadata_path = tmp_path / "metadata-nonopaque.png"
    metadata_path.write_bytes(
        _synthetic_png(
            rgba=True,
            alpha=0,
            metadata_chunks=(
                (b"vpAg", b"first"),
                (b"raNd", b"second"),
                (b"vpAg", b"third"),
            ),
        )
    )
    record = admit_generated_reference_png(metadata_path).technical_record
    assert record.alpha_status == "NON_OPAQUE"
    assert record.metadata_status == "PRESENT"
    assert record.metadata_chunk_types == ("vpAg", "raNd")


def test_outcome_builder_normalizes_json_lists_to_frozen_tuples(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    json_projection = json.loads(_canonical_compact(projection))
    assert type(json_projection["output_descriptors"]) is list
    assert (
        type(json_projection["output_descriptors"][0]["technical_record"]["metadata_chunk_types"])
        is list
    )

    rebuilt = build_generated_reference_provider_attempt_outcome(json_projection)
    assert type(rebuilt.output_descriptors) is tuple
    assert type(rebuilt.output_descriptors[0].technical_record.metadata_chunk_types) is tuple
    assert rebuilt.outcome_sha256 == (
        "27fb21abbe3e37bae4812ea0a156f8661ea79525c7045594a89cb8340df31b47"
    )


def test_formal_root_cardinality_allows_65_and_68_but_nested_65_fails(
    tmp_path: Path,
) -> None:
    closure = _closure(tmp_path)
    for value, expected_count in ((closure.outcome, 65), (closure.candidate, 68)):
        document = value.model_dump(mode="json")
        assert len(document) == expected_count
        assert type(value).model_validate_json(_canonical_document(document)) == value

    nested_oversize = closure.outcome.model_dump(mode="json")
    nested_oversize["output_descriptors"][0]["technical_record"]["oversize"] = {
        f"item_{index:02d}": index for index in range(65)
    }
    with pytest.raises(ValueError, match="contains too many keys"):
        CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.model_validate_json(
            _canonical_document(nested_oversize)
        )


def test_persistent_json_rejects_boolean_integer_substitution(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    candidate_document = closure.candidate.model_dump(mode="json")
    candidate_document["qualification_decision_embedded"] = 0
    with pytest.raises(ValueError, match="exact JSON boolean"):
        CreativeSampleGeneratedReferenceCandidateV1.model_validate_json(
            _canonical_document(candidate_document)
        )


@pytest.mark.parametrize(
    "closure_attribute",
    ["outcome", "candidate", "request", "decision"],
)
def test_all_four_formal_contracts_reject_every_numeric_boolean_type_alias(
    tmp_path: Path,
    closure_attribute: str,
) -> None:
    value = getattr(_closure(tmp_path), closure_attribute)
    python_document = value.model_dump(mode="python")
    json_document = value.model_dump(mode="json")
    paths = _numeric_boolean_leaf_paths(python_document)
    assert paths
    assert {_path_name(path) for path in paths} == {
        _path_name(path) for path in _numeric_boolean_leaf_paths(json_document)
    }

    for path in paths:
        original = _tree_leaf(python_document, path)
        assert type(original) in {bool, int}
        substituted = (
            int(original)
            if type(original) is bool
            else (bool(original) if original in {0, 1} else float(original))
        )
        assert substituted == original and type(substituted) is not type(original)

        with pytest.raises(ValueError):
            type(value).model_validate(_replace_tree_leaf(python_document, path, substituted))
        with pytest.raises(ValueError):
            type(value).model_validate_json(
                _canonical_document(_replace_tree_leaf(json_document, path, substituted))
            )


@pytest.mark.parametrize(
    ("closure_attribute", "field_name", "substituted"),
    [
        ("outcome", "attempt_ordinal", 1.0),
        ("candidate", "output_ordinal", "0"),
        ("request", "authorized_attempts", "0"),
        ("decision", "qualification_performed", 1.0),
    ],
)
def test_all_four_formal_contracts_reject_string_and_zero_one_float_aliases(
    tmp_path: Path,
    closure_attribute: str,
    field_name: str,
    substituted: object,
) -> None:
    value = getattr(_closure(tmp_path), closure_attribute)
    for mode in ("python", "json"):
        document = value.model_dump(mode=mode)
        document[field_name] = substituted
        with pytest.raises(ValueError):
            if mode == "python":
                type(value).model_validate(document)
            else:
                type(value).model_validate_json(_canonical_document(document))


def test_exact_model_instances_reject_root_and_nested_model_copy_type_pollution(
    tmp_path: Path,
) -> None:
    closure = _closure(tmp_path)
    polluted_candidate = closure.candidate.model_copy(update={"output_ordinal": False})
    with pytest.raises(ValueError):
        CreativeSampleGeneratedReferenceCandidateV1.model_validate(polluted_candidate)

    descriptor = closure.outcome.output_descriptors[0]
    polluted_record = descriptor.technical_record.model_copy(update={"interlaced": 0})
    polluted_descriptor = descriptor.model_copy(update={"technical_record": polluted_record})
    polluted_outcome = closure.outcome.model_copy(
        update={"output_descriptors": (polluted_descriptor,)}
    )
    with pytest.raises(ValueError):
        CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1.model_validate(polluted_outcome)


@pytest.mark.parametrize(
    ("expected_value", "substituted_value"),
    [(True, 1), (False, 0), (1, True), (0, False)],
)
def test_preparer_action_exact_record_rejects_boolean_integer_pseudo_equality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expected_value: object,
    substituted_value: object,
) -> None:
    closure = _closure(tmp_path)
    original_expected = generated_reference_candidate._request_preparer_action_expected

    def expected_with_type_sentinel(**kwargs: object) -> dict[str, object]:
        expected = original_expected(**kwargs)  # type: ignore[arg-type]
        expected["synthetic_exact_type_sentinel"] = expected_value
        return expected

    action = json.loads(closure.preparer_action)
    action["synthetic_exact_type_sentinel"] = substituted_value
    monkeypatch.setattr(
        generated_reference_candidate,
        "_request_preparer_action_expected",
        expected_with_type_sentinel,
    )
    with pytest.raises(GeneratedReferenceCandidateError):
        prepare_generated_reference_candidate_qualification_request(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=_canonical_document(action),
            requested_at="2026-08-29T01:02:00Z",
        )


def test_qualifier_action_rejects_true_one_and_false_zero_pseudo_equality(
    tmp_path: Path,
) -> None:
    closure = _closure(tmp_path)
    pass_gates = _gate_results(closure.evidence)
    true_as_one = json.loads(closure.qualifier_action)
    true_as_one["eligible_for_separate_generated_rights_manifest_review"] = 1
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=_canonical_document(true_as_one),
            decision_at="2026-08-29T01:03:00Z",
            gate_results=pass_gates,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )

    indeterminate_gates = list(pass_gates)
    indeterminate_gates[0] = indeterminate_gates[0].model_copy(update={"result": "INDETERMINATE"})
    gate_tuple = tuple(indeterminate_gates)
    issue_codes = ("PROVENANCE_CLOSURE_UNRESOLVED",)
    false_action = _qualifier_action(
        closure.request,
        gate_tuple,
        closure.qualifier_reference,
        issue_codes=issue_codes,
        decision="NEEDS_HUMAN_REVIEW",
        eligible=False,
    )
    false_as_zero = json.loads(false_action)
    false_as_zero["eligible_for_separate_generated_rights_manifest_review"] = 0
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=_canonical_document(false_as_zero),
            decision_at="2026-08-29T01:03:00Z",
            gate_results=gate_tuple,
            qualification_issue_codes=issue_codes,  # type: ignore[arg-type]
            qualification_basis="Synthetic independent human qualification closure.",
            decision="NEEDS_HUMAN_REVIEW",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("attempt_ordinal", 2),
        ("predecessor_outcome_id", "generated_reference_attempt_outcome_v1_deadbeefdeadbeefdead"),
        ("retry_authorized", True),
        ("retry_of_attempt_ordinal", 1),
        ("provider_task_id", "raw-provider-task-123"),
        ("signed_url", "https://example.invalid/output.png"),
        ("local_path", "C:/sensitive/output.png"),
        ("credential", "prohibited-secret"),
    ],
)
def test_v1_outcome_structurally_rejects_attempt_two_and_retry_fields(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection[field] = value
    with pytest.raises(GeneratedReferenceCandidateError):
        build_generated_reference_provider_attempt_outcome(projection)


@pytest.mark.parametrize(
    "updates",
    [
        {"terminal_observed_at": "2026-08-29T00:59:59Z"},
        {"provider_terms_observed_at": "2026-08-29T01:00:01Z"},
        {"provider_terms_valid_from": "2026-08-29T01:00:01Z"},
        {"provider_terms_valid_until": "2026-08-29T01:00:00Z"},
    ],
)
def test_outcome_rejects_temporal_drift(tmp_path: Path, updates: dict[str, object]) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection.update(updates)
    with pytest.raises(GeneratedReferenceCandidateError):
        build_generated_reference_provider_attempt_outcome(projection)


@pytest.mark.parametrize(
    "missing_field",
    [
        "attempt_provenance_record_sha256",
        "terminal_observation_record_sha256",
        "provider_terms_snapshot_sha256",
        "output_set_sha256",
    ],
)
def test_outcome_rejects_missing_caller_claims(tmp_path: Path, missing_field: str) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection.pop(missing_field)
    with pytest.raises(GeneratedReferenceCandidateError):
        build_generated_reference_provider_attempt_outcome(projection)


def test_outcome_rejects_mismatched_caller_output_set_digest(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection["output_set_sha256"] = "0" * 64
    with pytest.raises(GeneratedReferenceCandidateError):
        build_generated_reference_provider_attempt_outcome(projection)


def test_core_module_has_frozen_offline_dependency_and_capability_surface() -> None:
    source = Path(generated_reference_candidate.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    call_names: set[str] = set()
    open_calls: list[ast.Call] = []
    forbidden_write_calls = {
        "mkdir",
        "rename",
        "rmdir",
        "unlink",
        "write",
        "write_bytes",
        "write_text",
    }

    def qualified_name(node: ast.expr) -> str | None:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name):
            return None
        parts.append(current.id)
        return ".".join(reversed(parts))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            name = qualified_name(node.func)
            if name is not None:
                call_names.add(name)
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_write_calls
                if node.func.attr == "open":
                    open_calls.append(node)

    assert imported_modules <= {
        "__future__",
        "collections.abc",
        "dataclasses",
        "datetime",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "pydantic",
        "pydantic.config",
        "re",
        "sdc.visual_reference_prompt_compiler",
        "stat",
        "typing",
        "unicodedata",
        "zlib",
    }
    assert {name for name in imported_modules if name.startswith("sdc.")} == {
        "sdc.visual_reference_prompt_compiler"
    }
    assert "sdc.schemas" not in imported_modules
    assert call_names.isdisjoint(
        {
            "__import__",
            "compile",
            "date.today",
            "datetime.now",
            "datetime.utcnow",
            "eval",
            "exec",
            "os.getenv",
            "os.popen",
            "os.rename",
            "os.replace",
            "os.system",
            "os.urandom",
            "random.random",
            "secrets.token_bytes",
            "subprocess.Popen",
            "subprocess.run",
            "time.monotonic",
            "time.perf_counter",
            "time.time",
            "uuid.uuid4",
        }
    )
    assert len(open_calls) == 1
    assert (
        len(open_calls[0].args) == 1
        and isinstance(open_calls[0].args[0], ast.Constant)
        and open_calls[0].args[0].value == "rb"
        and not open_calls[0].keywords
    )
    folded = source.casefold()
    for marker in (
        "asyncpg",
        "datetime.now(",
        "datetime.utcnow(",
        "getenv(",
        "httpx.",
        "importlib",
        "os.environ",
        "random.",
        "requests.",
        "sdc.schemas",
        "secrets.",
        "socket.",
        "sqlalchemy",
        "subprocess.",
        "temporalio",
        "time.monotonic(",
        "time.perf_counter(",
        "time.time(",
        "urllib",
        "uuid4(",
    ):
        assert marker not in folded


def test_all_other_production_modules_have_no_generated_candidate_reverse_wiring() -> None:
    forbidden_references = (
        "sdc.generated_reference_candidate",
        "CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1",
        "CreativeSampleGeneratedReferenceCandidateV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationRequestV1",
        "CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1",
    )
    allowed_modules = {
        "generated_reference_candidate.py",
        "generated_reference_candidate_codegen.py",
        "generated_reference_asset_promotion.py",
        "generated_reference_asset_promotion_codegen.py",
        "generated_reference_rights_current_status.py",
        "generated_reference_rights_current_status_codegen.py",
        "schemas.py",
    }
    production_modules = tuple(sorted((ROOT / "src" / "sdc").glob("*.py")))
    assert production_modules
    for module_path in production_modules:
        if module_path.name in allowed_modules:
            continue
        source = module_path.read_text(encoding="utf-8")
        assert all(reference not in source for reference in forbidden_references)


def test_four_contracts_cannot_validate_as_job_provider_or_canary_inputs(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    documents = tuple(
        value.model_dump(mode="json")
        for value in (
            closure.outcome,
            closure.candidate,
            closure.request,
            closure.decision,
        )
    )
    execution_models = (
        GenerationJob,
        JobGraph,
        ProviderRequest,
        CanaryExecution,
        CanaryPlan,
        EvidenceBoundCanaryPlan,
    )
    for document in documents:
        for model in execution_models:
            with pytest.raises(ValidationError):
                model.model_validate(document)


def test_candidate_cannot_validate_as_asset_bible_or_input_material(tmp_path: Path) -> None:
    document = _closure(tmp_path).candidate.model_dump(mode="json")
    for model in (
        CharacterAssetVersion,
        SceneAssetVersion,
        CharacterBible,
        SceneBible,
        InputMaterial,
    ):
        with pytest.raises(ValidationError):
            model.model_validate(document)
    assert document["origin_claim"] != "IMPORTED_APPROVED_MEDIA"


def test_qc_and_provider_compatibility_cannot_automatically_influence_decision(
    tmp_path: Path,
) -> None:
    forbidden_fields = {
        "provider_compatibility",
        "provider_compatibility_observations",
        "provider_syntax_compatibility_observations",
        "qc_expectations",
    }
    for model in (
        CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
        CreativeSampleGeneratedReferenceCandidateV1,
        CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
        CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
    ):
        assert forbidden_fields.isdisjoint(model.model_fields)

    decision_projection = (
        creative_sample_generated_reference_candidate_qualification_decision_projection(
            _closure(tmp_path).decision
        )
    )

    def nested_keys(value: object) -> set[str]:
        if type(value) is dict:
            return set(value) | {key for nested in value.values() for key in nested_keys(nested)}
        if type(value) in {list, tuple}:
            return {key for nested in value for key in nested_keys(nested)}
        return set()

    assert forbidden_fields.isdisjoint(nested_keys(decision_projection))
    assert forbidden_fields.isdisjoint(
        record_generated_reference_candidate_qualification_decision.__annotations__
    )

    source = Path(generated_reference_candidate.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    semantic_identifiers: set[str] = set()
    semantic_strings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            semantic_identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            semantic_identifiers.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            semantic_strings.append(node.value)
    assert forbidden_fields.isdisjoint(semantic_identifiers)
    assert all(forbidden not in text for forbidden in forbidden_fields for text in semantic_strings)


def test_non_submission_evidence_cannot_be_perpetual_past_finite_effective_until(
    tmp_path: Path,
) -> None:
    closure = _closure(tmp_path)
    evidence = list(closure.evidence)
    index = EVIDENCE_CATEGORY_ORDER.index("OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE")
    original = evidence[index]
    document = json.loads(original.document_bytes)
    document["evidence_valid_until"] = "PERPETUAL"
    raw = _canonical_document(document)
    reference = GeneratedReferenceQualificationEvidenceReferenceV1.model_validate(
        {
            **original.reference.model_dump(mode="python"),
            "document_size_bytes": len(raw),
            "document_sha256": hashlib.sha256(raw).hexdigest(),
            "evidence_valid_until": "PERPETUAL",
        }
    )
    evidence[index] = GeneratedReferenceQualificationEvidenceInput(
        reference=reference,
        document_bytes=raw,
    )
    changed_evidence = tuple(evidence)
    preparer_action = _preparer_action(
        closure.candidate,
        closure.outcome,
        changed_evidence,
        closure.preparer_reference,
    )

    with pytest.raises(GeneratedReferenceCandidateError):
        prepare_generated_reference_candidate_qualification_request(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            png_path=closure.png_path,
            evidence_documents=changed_evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=preparer_action,
            requested_at="2026-08-29T01:02:00Z",
        )


@pytest.mark.parametrize(
    ("category", "updates"),
    [
        ("PROVIDER_TERMS_AT_SUBMISSION", {"record_id": "different-terms-record"}),
        (
            "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
            {"observed_at": "2026-08-29T01:03:00Z"},
        ),
        (
            "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
            {"evidence_valid_until": "2026-08-29T01:02:00Z"},
        ),
        (
            "INPUT_TEXT_AND_MEDIA_RIGHTS_AT_SUBMISSION",
            {"effective_from": "2026-08-29T01:00:01Z"},
        ),
        (
            "OUTPUT_COPYRIGHT_AND_COMMERCIAL_SCOPE",
            {"effective_from": "2026-08-29T01:03:00Z"},
        ),
    ],
)
def test_qualification_request_rejects_terms_and_freshness_drift(
    tmp_path: Path,
    category: str,
    updates: dict[str, object],
) -> None:
    closure = _closure(tmp_path)
    evidence = _mutated_evidence_documents(closure.evidence, category, **updates)
    preparer_action = _preparer_action(
        closure.candidate,
        closure.outcome,
        evidence,
        closure.preparer_reference,
    )
    with pytest.raises(GeneratedReferenceCandidateError):
        prepare_generated_reference_candidate_qualification_request(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            png_path=closure.png_path,
            evidence_documents=evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=preparer_action,
            requested_at="2026-08-29T01:02:00Z",
        )


@pytest.mark.parametrize(
    "alias_name",
    [
        "evidence_document",
        "policy_document",
        "artifact_domain",
        "outcome_domain",
        "candidate_domain",
        "output_set_domain",
        "png_technical_record_domain",
        "png_content_raw",
        "profile_nested",
        "catalog_nested",
        "render_input_nested",
        "prompt_receipt_nested",
    ],
)
def test_qualification_request_rejects_every_formal_digest_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alias_name: str,
) -> None:
    closure = _closure(tmp_path)
    original_raw_sha256 = generated_reference_candidate._raw_sha256
    aliased_digest = _formal_digest_aliases(closure, include_request=False)[alias_name]

    def forced_alias(raw: bytes) -> str:
        if raw == closure.preparer_action:
            return aliased_digest
        return original_raw_sha256(raw)

    monkeypatch.setattr(generated_reference_candidate, "_raw_sha256", forced_alias)
    with pytest.raises(GeneratedReferenceCandidateError):
        prepare_generated_reference_candidate_qualification_request(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            requested_at="2026-08-29T01:02:00Z",
        )


@pytest.mark.parametrize(
    "alias_name",
    [
        "evidence_document",
        "policy_document",
        "artifact_domain",
        "outcome_domain",
        "candidate_domain",
        "request_domain",
        "output_set_domain",
        "png_technical_record_domain",
        "png_content_raw",
        "profile_nested",
        "catalog_nested",
        "render_input_nested",
        "prompt_receipt_nested",
    ],
)
def test_qualification_decision_rejects_every_formal_digest_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alias_name: str,
) -> None:
    closure = _closure(tmp_path)
    original_raw_sha256 = generated_reference_candidate._raw_sha256
    aliased_digest = _formal_digest_aliases(closure, include_request=True)[alias_name]

    def forced_alias(raw: bytes) -> str:
        if raw == closure.qualifier_action:
            return aliased_digest
        return original_raw_sha256(raw)

    monkeypatch.setattr(generated_reference_candidate, "_raw_sha256", forced_alias)
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=closure.qualifier_action,
            decision_at="2026-08-29T01:03:00Z",
            gate_results=_gate_results(closure.evidence),
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )


@pytest.mark.parametrize("variant", ["missing", "reordered", "duplicate", "raw_drift"])
def test_qualification_request_rejects_incomplete_or_drifted_evidence_set(
    tmp_path: Path,
    variant: str,
) -> None:
    closure = _closure(tmp_path)
    if variant == "missing":
        evidence = closure.evidence[:-1]
    elif variant == "reordered":
        evidence = (closure.evidence[1], closure.evidence[0], *closure.evidence[2:])
    elif variant == "duplicate":
        evidence = (closure.evidence[0], closure.evidence[0], *closure.evidence[2:])
    else:
        original = closure.evidence[4]
        document = json.loads(original.document_bytes)
        document["synthetic_known_answer"] = "reviewed-drift"
        drifted = GeneratedReferenceQualificationEvidenceInput(
            reference=original.reference,
            document_bytes=_canonical_document(document),
        )
        evidence = (*closure.evidence[:4], drifted, *closure.evidence[5:])
    with pytest.raises(GeneratedReferenceCandidateError):
        prepare_generated_reference_candidate_qualification_request(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            png_path=closure.png_path,
            evidence_documents=evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            requested_at="2026-08-29T01:02:00Z",
        )


@pytest.mark.parametrize(
    ("disposition", "task_status", "count", "overflow", "reason"),
    [
        ("SUBMISSION_REJECTED", "ABSENT", 0, False, "SUBMISSION_REJECTED_BY_PROVIDER"),
        (
            "PROVIDER_TASK_FAILED",
            "PRESENT_IN_RETAINED_RECORD",
            0,
            False,
            "PROVIDER_TASK_REPORTED_FAILURE",
        ),
        ("CANCELLED", "PRESENT_IN_RETAINED_RECORD", 0, False, "PROVIDER_TASK_CANCELLED"),
        (
            "EXPIRED",
            "PRESENT_IN_RETAINED_RECORD",
            0,
            False,
            "PROVIDER_TASK_EXPIRED_OR_TIMED_OUT",
        ),
        ("SUBMISSION_UNKNOWN", "ABSENT", 0, False, "SUBMISSION_RESULT_UNKNOWN"),
        (
            "SUBMISSION_UNKNOWN",
            "PRESENT_IN_RETAINED_RECORD",
            0,
            False,
            "SUBMISSION_RESULT_UNKNOWN",
        ),
        (
            "PARTIAL_OUTPUT",
            "PRESENT_IN_RETAINED_RECORD",
            0,
            False,
            "EXPECTED_OUTPUT_NOT_FULLY_AVAILABLE",
        ),
        (
            "PARTIAL_OUTPUT",
            "PRESENT_IN_RETAINED_RECORD",
            1,
            False,
            "EXPECTED_OUTPUT_NOT_FULLY_AVAILABLE",
        ),
        (
            "OUTPUT_INTEGRITY_FAILURE",
            "PRESENT_IN_RETAINED_RECORD",
            1,
            False,
            "OUTPUT_BYTES_OR_TECHNICAL_RECORD_MISMATCH",
        ),
        (
            "UNSUPPORTED_OUTPUT_CARDINALITY",
            "PRESENT_IN_RETAINED_RECORD",
            2,
            False,
            "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
        ),
        (
            "UNSUPPORTED_OUTPUT_CARDINALITY",
            "PRESENT_IN_RETAINED_RECORD",
            64,
            True,
            "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
        ),
    ],
)
def test_every_non_success_terminal_shape_is_evidence_only(
    tmp_path: Path,
    disposition: str,
    task_status: str,
    count: int,
    overflow: bool,
    reason: str,
) -> None:
    path = tmp_path / "reference.png"
    path.write_bytes(_synthetic_png())
    descriptor = admit_generated_reference_png(path)
    artifact = _artifact()
    evidence = _evidence_documents()
    success = _outcome(artifact, descriptor, evidence)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(success)
    projection.update(
        {
            "terminal_disposition": disposition,
            "terminal_reason_code": reason,
            "provider_task_reference_status": task_status,
            "reported_output_count_bounded": count,
            "reported_output_count_overflow": overflow,
            "verified_output_count": 0,
            "output_descriptors": [],
        }
    )
    outcome = build_generated_reference_provider_attempt_outcome(
        _bind_output_set_sha256(projection)
    )
    assert outcome.terminal_disposition == disposition
    with pytest.raises(GeneratedReferenceCandidateError):
        capture_generated_reference_candidate(artifact, outcome, png_path=path)


@pytest.mark.parametrize(
    "updates",
    [
        {"reported_output_count_bounded": 2},
        {"provider_task_reference_status": "ABSENT"},
        {
            "terminal_disposition": "UNSUPPORTED_OUTPUT_CARDINALITY",
            "terminal_reason_code": "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
            "reported_output_count_bounded": 1,
            "verified_output_count": 0,
            "output_descriptors": [],
        },
        {
            "terminal_disposition": "UNSUPPORTED_OUTPUT_CARDINALITY",
            "terminal_reason_code": "PROVIDER_REPORTED_UNSUPPORTED_OUTPUT_COUNT",
            "reported_output_count_bounded": 63,
            "reported_output_count_overflow": True,
            "verified_output_count": 0,
            "output_descriptors": [],
        },
        {
            "terminal_disposition": "PARTIAL_OUTPUT",
            "terminal_reason_code": "EXPECTED_OUTPUT_NOT_FULLY_AVAILABLE",
            "reported_output_count_overflow": True,
            "verified_output_count": 0,
            "output_descriptors": [],
        },
        {
            "terminal_disposition": "SUBMISSION_REJECTED",
            "terminal_reason_code": "SUBMISSION_REJECTED_BY_PROVIDER",
            "provider_task_reference_status": "ABSENT",
            "reported_output_count_bounded": 0,
        },
    ],
)
def test_terminal_matrix_rejects_cross_row_combinations(
    tmp_path: Path,
    updates: dict[str, object],
) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection.update(updates)
    with pytest.raises(GeneratedReferenceCandidateError):
        build_generated_reference_provider_attempt_outcome(_bind_output_set_sha256(projection))


def test_identity_separation_and_gate_mapping_fail_closed(tmp_path: Path) -> None:
    closure = _closure(tmp_path)
    gates = _gate_results(closure.evidence)
    same_identity = closure.preparer_reference
    action = _qualifier_action(closure.request, gates, same_identity)
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=same_identity,
            qualifier_action_bytes=action,
            decision_at="2026-08-29T01:03:00Z",
            gate_results=gates,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )


@pytest.mark.parametrize(
    "historical_status",
    ["CLAIMED_ABSENT", "UNKNOWN"],
)
def test_absent_or_unknown_historical_authorization_cannot_pass_remote_gate(
    tmp_path: Path,
    historical_status: str,
) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection["historical_execution_authorization_status"] = historical_status
    outcome = build_generated_reference_provider_attempt_outcome(projection)
    candidate, request, preparer_action = _prepare_changed_outcome(closure, outcome)
    gates = _gate_results(closure.evidence)
    qualifier_action = _qualifier_action(request, gates, closure.qualifier_reference)

    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            outcome,
            candidate,
            request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=qualifier_action,
            decision_at="2026-08-29T01:03:00Z",
            gate_results=gates,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )


@pytest.mark.parametrize(
    ("historical_status", "gate_result", "issue_codes", "decision"),
    [
        (
            "CLAIMED_ABSENT",
            "FAIL",
            (
                "REMOTE_PROCESSING_AUTHORIZATION_UNRESOLVED_OR_ABSENT",
                "QUALIFIER_REJECTED",
            ),
            "REJECTED",
        ),
        (
            "UNKNOWN",
            "INDETERMINATE",
            ("REMOTE_PROCESSING_AUTHORIZATION_UNRESOLVED_OR_ABSENT",),
            "NEEDS_HUMAN_REVIEW",
        ),
    ],
)
def test_absent_or_unknown_historical_authorization_closes_only_as_non_pass(
    tmp_path: Path,
    historical_status: str,
    gate_result: str,
    issue_codes: tuple[str, ...],
    decision: str,
) -> None:
    closure = _closure(tmp_path)
    projection = creative_sample_generated_reference_provider_attempt_outcome_projection(
        closure.outcome
    )
    projection["historical_execution_authorization_status"] = historical_status
    outcome = build_generated_reference_provider_attempt_outcome(projection)
    candidate, request, preparer_action = _prepare_changed_outcome(closure, outcome)
    gates = list(_gate_results(closure.evidence))
    remote_index = QUALIFICATION_GATE_ORDER.index("REMOTE_PROCESSING_AUTHORIZED_AT_SUBMISSION")
    gates[remote_index] = gates[remote_index].model_copy(
        update={
            "result": gate_result,
            "basis": "Synthetic historical authorization non-PASS known-answer.",
        }
    )
    gate_tuple = tuple(gates)
    qualifier_action = _qualifier_action(
        request,
        gate_tuple,
        closure.qualifier_reference,
        issue_codes=issue_codes,
        decision=decision,
        eligible=False,
    )

    recorded = record_generated_reference_candidate_qualification_decision(
        closure.artifact,
        outcome,
        candidate,
        request,
        png_path=closure.png_path,
        evidence_documents=closure.evidence,
        preparer_reference_bytes=closure.preparer_reference,
        preparer_action_bytes=preparer_action,
        qualifier_reference_bytes=closure.qualifier_reference,
        qualifier_action_bytes=qualifier_action,
        decision_at="2026-08-29T01:03:00Z",
        gate_results=gate_tuple,
        qualification_issue_codes=issue_codes,  # type: ignore[arg-type]
        qualification_basis="Synthetic independent human qualification closure.",
        decision=decision,  # type: ignore[arg-type]
    )
    assert recorded.qualification_issue_codes == issue_codes
    assert recorded.decision == decision
    assert recorded.eligible_for_separate_generated_rights_manifest_review is False


@pytest.mark.parametrize(
    ("gate_result", "issue_codes", "decision"),
    [
        (
            "INDETERMINATE",
            ("PROVENANCE_CLOSURE_UNRESOLVED",),
            "NEEDS_HUMAN_REVIEW",
        ),
        (
            "FAIL",
            ("PROVENANCE_CLOSURE_UNRESOLVED", "QUALIFIER_REJECTED"),
            "REJECTED",
        ),
    ],
)
def test_non_pass_decision_matrix_is_exact(
    tmp_path: Path,
    gate_result: str,
    issue_codes: tuple[str, ...],
    decision: str,
) -> None:
    closure = _closure(tmp_path)
    gates = list(_gate_results(closure.evidence))
    gates[0] = gates[0].model_copy(
        update={
            "result": gate_result,
            "basis": "Synthetic first-party non-PASS human known-answer.",
        }
    )
    gate_tuple = tuple(gates)
    qualifier_action = _qualifier_action(
        closure.request,
        gate_tuple,
        closure.qualifier_reference,
        issue_codes=issue_codes,
        decision=decision,
        eligible=False,
    )
    recorded = record_generated_reference_candidate_qualification_decision(
        closure.artifact,
        closure.outcome,
        closure.candidate,
        closure.request,
        png_path=closure.png_path,
        evidence_documents=closure.evidence,
        preparer_reference_bytes=closure.preparer_reference,
        preparer_action_bytes=closure.preparer_action,
        qualifier_reference_bytes=closure.qualifier_reference,
        qualifier_action_bytes=qualifier_action,
        decision_at="2026-08-29T01:03:00Z",
        gate_results=gate_tuple,
        qualification_issue_codes=issue_codes,  # type: ignore[arg-type]
        qualification_basis="Synthetic independent human qualification closure.",
        decision=decision,  # type: ignore[arg-type]
    )
    assert recorded.qualification_issue_codes == issue_codes
    assert recorded.decision == decision
    assert recorded.eligible_for_separate_generated_rights_manifest_review is False


def test_frozen_orders_and_half_open_decision_time_are_enforced(tmp_path: Path) -> None:
    assert len(EVIDENCE_CATEGORY_ORDER) == 10
    assert len(QUALIFICATION_GATE_ORDER) == 15
    assert len(QUALIFICATION_ISSUE_CODE_ORDER) == 16
    closure = _closure(tmp_path)
    gates = _gate_results(closure.evidence)
    lower_action = _qualifier_action(
        closure.request,
        gates,
        closure.qualifier_reference,
        decision_at=closure.request.requested_at,
    )
    lower_bound = record_generated_reference_candidate_qualification_decision(
        closure.artifact,
        closure.outcome,
        closure.candidate,
        closure.request,
        png_path=closure.png_path,
        evidence_documents=closure.evidence,
        preparer_reference_bytes=closure.preparer_reference,
        preparer_action_bytes=closure.preparer_action,
        qualifier_reference_bytes=closure.qualifier_reference,
        qualifier_action_bytes=lower_action,
        decision_at=closure.request.requested_at,
        gate_results=gates,
        qualification_issue_codes=(),
        qualification_basis="Synthetic independent human qualification closure.",
        decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
    )
    assert lower_bound.decision_at == closure.request.requested_at

    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=closure.qualifier_action,
            decision_at="2026-08-29T01:01:59Z",
            gate_results=gates,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=closure.qualifier_action,
            decision_at=closure.request.request_valid_until,
            gate_results=gates,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )
    first = gates[0].model_copy(update={"evidence_record_ids": ()})
    drifted = (first, *gates[1:])
    with pytest.raises(GeneratedReferenceCandidateError):
        record_generated_reference_candidate_qualification_decision(
            closure.artifact,
            closure.outcome,
            closure.candidate,
            closure.request,
            png_path=closure.png_path,
            evidence_documents=closure.evidence,
            preparer_reference_bytes=closure.preparer_reference,
            preparer_action_bytes=closure.preparer_action,
            qualifier_reference_bytes=closure.qualifier_reference,
            qualifier_action_bytes=closure.qualifier_action,
            decision_at="2026-08-29T01:03:00Z",
            gate_results=drifted,
            qualification_issue_codes=(),
            qualification_basis="Synthetic independent human qualification closure.",
            decision="PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW",
        )


def test_bounded_valid_until_handles_year_9999_without_bare_overflow() -> None:
    assert (
        generated_reference_candidate._bounded_valid_until(
            "9999-12-31T00:00:00Z",
            "9999-12-31T12:00:00Z",
        )
        == "9999-12-31T12:00:00Z"
    )
    with pytest.raises(ValueError, match="representable 24-hour UTC cap"):
        generated_reference_candidate._bounded_valid_until(
            "9999-12-31T23:59:59Z",
            "PERPETUAL",
        )
