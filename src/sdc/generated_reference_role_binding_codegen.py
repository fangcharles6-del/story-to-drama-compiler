"""Repository-only known-answer codegen for ADR-046 role-binding evidence.

The command has one deliberately narrow persistence exception: ``--update`` may write the one
fixed derived JSON fixture.  ``--check`` is read-only.  Both modes verify the separately reviewed
source packet and every one of the eighteen pre-ADR-046 visual-prompt fixtures by exact bytes before
deriving any value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Never, cast

from sdc import generated_reference_asset_promotion as promotion_module
from sdc import generated_reference_asset_promotion_codegen as promotion_codegen
from sdc import generated_reference_role_binding as role_module

_KNOWN_ANSWER_VERSION = "1.0.0"
_POLICY_DOCUMENT_SHA256 = (
    "fd57663ac40e7c6b9a6c64dc24dff0d28acdfb3529a7d267bbd82e047bb64233"
)
_FIXTURE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated-reference-role-binding"
_REVIEWED_SOURCE_PATH = f"{_FIXTURE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_DERIVED_FIXTURE_PATH = f"{_FIXTURE_DIRECTORY}/generated-known-answer-v1.json"
_PROMOTION_DIRECTORY = (
    "tests/fixtures/visual_prompt_profiles/generated-reference-asset-promotion"
)
_PROMOTION_SOURCE_PATH = f"{_PROMOTION_DIRECTORY}/reviewed-known-answer-source-v1.json"
_PROMOTION_GENERATED_PATH = f"{_PROMOTION_DIRECTORY}/generated-known-answer-v1.json"

# This is the complete pre-ADR-046 tracked visual-prompt fixture inventory.  It is intentionally a
# literal map, never a discovered directory listing.  The two ADR-046 paths are excluded.
_FROZEN_OLD_FIXTURE_FINGERPRINTS: dict[str, tuple[int, str]] = {
    "tests/fixtures/visual_prompt_profiles/compiler-integration/reviewed-known-answer-v1.json": (
        26_163,
        "40b42f406f76fef0a07f1a810d7ff4853f7f765edd48e8e998d1504fdfc0336e",
    ),
    _PROMOTION_GENERATED_PATH: (
        720_716,
        "a587cb4bbf667f8ffe57b5f302ec16bfa3f98509b08ce49e965fe32e1c05bdee",
    ),
    _PROMOTION_SOURCE_PATH: (
        68_555,
        "633483d40e8404b2bbe9fc3fa370993b0e6b94148e61507d15962811957257ba",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-candidate/"
        "character-reference-synthetic-v1.png"
    ): (
        5_841,
        "3c20c94c18fbd72b68a58748bae9aba2daefc6baa38e9fc1c6ab30b40e6f39fc",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-candidate/"
        "generated-known-answer-v1.json"
    ): (
        84_090,
        "aaaf5fed96b2e867a99debf9ddfcc2759febd6e87ccb7defef3e4ae5f0b120a3",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-candidate/"
        "reviewed-known-answer-source-v1.json"
    ): (
        101_487,
        "b385164d9dabd467308250da41166e1a0d47b8cf8504eb15b5644590aa9edb55",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-candidate/"
        "scene-reference-synthetic-v1.png"
    ): (
        5_754,
        "97019f80b032242f33963836ce661e8761add311cdc7f8bd7b63ac247c0e5574",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status/"
        "generated-known-answer-v1.json"
    ): (
        294_275,
        "f043c46eabddd07fb8a18c73fca267f8e523e29da8aebb7df95a7e98ae196c75",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status/"
        "reviewed-known-answer-source-v1.json"
    ): (
        46_739,
        "d6c74ecb90c4c14abe47dbbd3d4ecd8fff8d5a4e0e90dbb2edae166773160315",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "character-reference-basic.prompt-render-receipt.json"
    ): (
        1_452,
        "2510e83345bc930d219e112b4c4e21834f98876cb205170d452cfedfa1e7f480",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/character-reference-basic.prompt.txt": (
        2_552,
        "7652c02a6abba5d7bf4fc85d296d70c23328dc98913c89bfcaf98f948f54fd87",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "narrative-shot-unicode.prompt-render-receipt.json"
    ): (
        1_447,
        "dda168d064a9c5e1ed2ed6992854bed550d2745a7c594f3cad695937dd419b55",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/narrative-shot-unicode.prompt.txt": (
        1_913,
        "3cf46430509bfe46c36d88b48133fba477d147bf536f58110ec8ffd1adcab5c4",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "scene-reference-basic.prompt-render-receipt.json"
    ): (
        1_448,
        "d4a5aa90b9f62718ffae6dd9f687f69b109039828608149b7c3945dfccdac93f",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/scene-reference-basic.prompt.txt": (
        2_232,
        "fb60a6daabd7b587a0c2759de254fd3812a3fa029a45767956c65e9f9ca838a9",
    ),
    "tests/fixtures/visual_prompt_profiles/reference-compiler/generated-known-answer-v1.json": (
        51_645,
        "0311fdf4ec54a36b3a3b3895c32dd7bbe453fdbbbde37de67db22d9c914b59a8",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/reference-compiler/"
        "reviewed-known-answer-source-v1.json"
    ): (
        14_587,
        "be072fe5be5ef4b35c2e482db3e60c14641bce8cf80eb95398d9a4468750170c",
    ),
    "tests/fixtures/visual_prompt_profiles/reviewed-known-answer-v1.json": (
        17_678,
        "0b736f1759fc23e4e809f278f978843099cbe98b24e3a4a9359de5274b39ae75",
    ),
}

_REVIEWED_SOURCE_FINGERPRINT = (
    13_198,
    "b90c9249e6c95f9738bac204d8ff973937549d0af602d0034bf95514a406f1a8",
)
_PROTECTED_FINGERPRINTS: dict[str, tuple[int, str]] = {
    _REVIEWED_SOURCE_PATH: _REVIEWED_SOURCE_FINGERPRINT,
    **_FROZEN_OLD_FIXTURE_FINGERPRINTS,
}

_MAX_SOURCE_BYTES = 2_097_152
_MAX_DERIVED_BYTES = 8_388_608
_MAX_OLD_FIXTURE_BYTES = 4_194_304
_MAX_PNG_BYTES = 67_108_864
_MAX_REPOSITORY_METADATA_BYTES = 262_144
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400

_CASE_IDS = ("character-role-binding-v1", "scene-role-binding-v1")
_PROMOTION_CASE_IDS = (
    "character-same-status-record-v1",
    "scene-successor-reconciliation-v1",
)
_ROLE_ORDER = {
    "CHARACTER_REFERENCE_ASSET": (
        "CHARACTER_IDENTITY_SHEET",
        "CHARACTER_POSE_REFERENCE",
        "CHARACTER_EXPRESSION_REFERENCE",
    ),
    "SCENE_REFERENCE_ASSET": (
        "SCENE_ESTABLISHING_REFERENCE",
        "SCENE_LIGHTING_REFERENCE",
        "SCENE_MATERIAL_REFERENCE",
        "SCENE_PROP_PLACEMENT_REFERENCE",
    ),
}
_HUMAN_GATE_ORDER = (
    "HUMAN_EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTED_WITHOUT_EXPANSION_ACKNOWLEDGED",
    "HUMAN_WHOLE_COMPOSITE_ROLE_SUITABILITY_APPROVED",
    "HUMAN_NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_ACKNOWLEDGED",
)
_EXPECTED_DECISIONS = {
    "character-identity-sheet-positive-v1": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "character-pose-rejected-v1": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
    "character-expression-indeterminate-v1": "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
    "scene-establishing-positive-v1": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "scene-lighting-positive-v1": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "scene-material-positive-v1": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
    "scene-prop-placement-positive-v1": "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
}


class GeneratedReferenceRoleBindingCodegenError(ValueError):
    """Stable local failure for the fixed ADR-046 codegen boundary."""


def _fail(message: str) -> Never:
    raise GeneratedReferenceRoleBindingCodegenError(message)


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _semantic_sha256(domain: bytes, projection: object) -> str:
    try:
        raw = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            "semantic projection is not compact canonical JSON"
        ) from exc
    return hashlib.sha256(domain + raw).hexdigest()


def _canonical_document_bytes(value: object) -> bytes:
    try:
        return promotion_codegen._canonical_document_bytes(value)
    except (
        TypeError,
        ValueError,
        promotion_codegen.GeneratedReferenceAssetPromotionCodegenError,
    ) as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            "value is not canonical persistent JSON"
        ) from exc


def _parse_canonical_document(raw: bytes, *, label: str) -> dict[str, object]:
    try:
        return promotion_codegen._parse_canonical_document(raw, label=label)
    except promotion_codegen.GeneratedReferenceAssetPromotionCodegenError as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            f"{label} is not exact canonical persistent JSON"
        ) from exc


def _is_reparse(info: os.stat_result) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT_ATTRIBUTE)


def _is_regular_single_file(info: os.stat_result) -> bool:
    return stat.S_ISREG(info.st_mode) and not _is_reparse(info) and info.st_nlink == 1


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _assert_fixed_paths() -> None:
    paths = (*_PROTECTED_FINGERPRINTS, _DERIVED_FIXTURE_PATH)
    if len(paths) != len(set(paths)):
        _fail("source, old fixtures and derived fixture paths must be distinct")
    if len(_FROZEN_OLD_FIXTURE_FINGERPRINTS) != 18:
        _fail("the frozen old visual-prompt fixture inventory must contain exactly eighteen paths")
    if _PROMOTION_SOURCE_PATH not in _FROZEN_OLD_FIXTURE_FINGERPRINTS or (
        _PROMOTION_GENERATED_PATH not in _FROZEN_OLD_FIXTURE_FINGERPRINTS
    ):
        _fail("the complete ADR-045 source and derived fixtures must be frozen upstream inputs")
    for value in paths:
        path = Path(value)
        if (
            path.is_absolute()
            or "\\" in value
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or ":" in path.parts[0]
        ):
            _fail("a fixed fixture path is not canonical repository-relative POSIX text")
    if Path(_REVIEWED_SOURCE_PATH).parent != Path(_FIXTURE_DIRECTORY) or Path(
        _DERIVED_FIXTURE_PATH
    ).parent != Path(_FIXTURE_DIRECTORY):
        _fail("ADR-046 source and derived fixtures must share their one fixed directory")


def _safe_path(root: Path, relative_path: str, *, label: str) -> Path:
    try:
        return promotion_codegen._safe_path(root, relative_path, label=label)
    except promotion_codegen.GeneratedReferenceAssetPromotionCodegenError as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            f"{label} is outside the fixed repository layout"
        ) from exc


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    try:
        return promotion_codegen._read_stable_regular_file(
            path,
            max_bytes=max_bytes,
            label=label,
        )
    except promotion_codegen.GeneratedReferenceAssetPromotionCodegenError as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            f"{label} could not be read as one stable regular file"
        ) from exc


def _read_frozen(
    root: Path,
    relative_path: str,
    *,
    max_bytes: int,
    label: str,
) -> bytes:
    path = _safe_path(root, relative_path, label=label)
    raw = _read_stable_regular_file(path, max_bytes=max_bytes, label=label)
    expected_size, expected_sha = _PROTECTED_FINGERPRINTS[relative_path]
    if expected_size <= 0 or len(expected_sha) != 64:
        _fail("a protected source byte anchor has not been frozen")
    if len(raw) != expected_size or _raw_sha256(raw) != expected_sha:
        _fail(f"{label} does not have its frozen exact bytes")
    return raw


def _identity_record(value: object, *, label: str) -> tuple[str, str]:
    if type(value) is not dict:
        _fail(f"{label} must be one exact identity object")
    identity = cast(dict[str, object], value)
    if set(identity) != {"document_profile", "identity_namespace", "identity_ref"} or identity.get(
        "document_profile"
    ) != "sdc.privacy-minimized-human-reference.v1":
        _fail(f"{label} is outside the exact privacy-minimized identity profile")
    namespace = identity.get("identity_namespace")
    reference = identity.get("identity_ref")
    if type(namespace) is not str or type(reference) is not str or not namespace or not reference:
        _fail(f"{label} identity tuple is not bounded text")
    return namespace, reference


def _bounded_text(value: object, *, label: str) -> str:
    if type(value) is not str or not 1 <= len(value) <= 1000 or value != value.strip():
        _fail(f"{label} must be one bounded trimmed human basis")
    return value


def _assert_boundary_checks(value: object) -> dict[str, object]:
    if type(value) is not dict:
        _fail("source boundary_checks must be one exact object")
    checks = cast(dict[str, object], value)
    expected_names = {
        "equal_bytes_distinct_candidate_occurrence",
        "fresh_replay",
        "primary_binding_attack",
        "prohibited_field_attacks",
        "rights_scope_attacks",
        "whole_media_boundary_attacks",
    }
    if set(checks) != expected_names:
        _fail("source boundary_checks do not close the reviewed ADR-046 attack matrix")
    prohibited = checks["prohibited_field_attacks"]
    if type(prohibited) is not dict or cast(dict[str, object], prohibited).get("field_names") != [
        "executable_route",
        "input_material",
        "provider_request",
        "provider_slot",
    ]:
        _fail("source prohibited-field attack order drifted")
    rights = checks["rights_scope_attacks"]
    if type(rights) is not dict or cast(dict[str, object], rights).get("mutations") != [
        "EXPANSION",
        "NARROWING",
        "REORDER",
        "RENEWAL_OR_EXTENSION",
    ]:
        _fail("source Rights-scope attack order drifted")
    media = checks["whole_media_boundary_attacks"]
    if type(media) is not dict or cast(dict[str, object], media).get("mutations") != [
        "CROP",
        "SPLIT",
        "PROVIDER_INPUT",
    ]:
        _fail("source whole-media attack order drifted")
    replay = checks["fresh_replay"]
    if type(replay) is not dict or cast(dict[str, object], replay).get(
        "expected_transition_count"
    ) != 2:
        _fail("source must require both exact role-binding fresh replay transitions")
    return checks


def _assert_source_shape(value: dict[str, object]) -> tuple[dict[str, object], ...]:
    if set(value) != {
        "boundary_checks",
        "cases",
        "known_answer_version",
        "source_packet_scope",
    }:
        _fail("reviewed source root fields drifted")
    if value.get("known_answer_version") != _KNOWN_ANSWER_VERSION or value.get(
        "source_packet_scope"
    ) != "FIRST_PARTY_FICTIONAL_SYNTHETIC_GENERATED_REFERENCE_ROLE_BINDING_REVIEW_ONLY":
        _fail("reviewed source identity drifted")
    _assert_boundary_checks(value["boundary_checks"])
    cases = value.get("cases")
    if type(cases) is not list or len(cases) != 2:
        _fail("reviewed source must contain exactly one Character and one Scene case")
    typed_cases: list[dict[str, object]] = []
    observed_roles: list[str] = []
    observed_decisions: set[str] = set()
    for ordinal, raw_case in enumerate(cast(list[object], cases)):
        if type(raw_case) is not dict:
            _fail("reviewed source cases must be exact objects")
        case = cast(dict[str, object], raw_case)
        if set(case) != {
            "asset_purpose",
            "binding_at_source",
            "case_id",
            "checker_identity_record",
            "first_party_synthetic_subject",
            "maker_identity_record",
            "promotion_case_id",
            "requested_at_source",
            "role_reviews",
            "status_plan",
        }:
            _fail("a reviewed source case field set drifted")
        purpose = case.get("asset_purpose")
        if (
            case.get("case_id") != _CASE_IDS[ordinal]
            or case.get("promotion_case_id") != _PROMOTION_CASE_IDS[ordinal]
            or purpose != tuple(_ROLE_ORDER)[ordinal]
            or case.get("first_party_synthetic_subject") is not True
            or case.get("requested_at_source") != "USE_PROMOTION_AT"
            or case.get("binding_at_source") != "USE_PROMOTION_AT"
            or case.get("status_plan")
            != (
                "PROMOTION_FINAL_EQUALS_REQUEST_STATUS_EQUALS_BINDING_FINAL_STATUS_"
                "WITH_TWO_EXACT_REPLAYS"
            )
        ):
            _fail("a reviewed Character/Scene source anchor drifted")
        maker = _identity_record(case.get("maker_identity_record"), label="Role-Binding Maker")
        checker = _identity_record(
            case.get("checker_identity_record"), label="Role-Binding Checker"
        )
        if maker == checker:
            _fail("Role-Binding Maker and Checker source identities must differ")
        reviews = case.get("role_reviews")
        expected_roles = _ROLE_ORDER[purpose]
        if type(reviews) is not list or len(reviews) != len(expected_roles):
            _fail("a reviewed case must contain the complete purpose role tuple")
        for role_ordinal, raw_review in enumerate(cast(list[object], reviews)):
            if type(raw_review) is not dict:
                _fail("role review source entries must be exact objects")
            review = cast(dict[str, object], raw_review)
            if set(review) != {
                "decision_basis",
                "expected_decision",
                "human_gate_results",
                "request_basis",
                "review_id",
                "selected_reference_role",
            }:
                _fail("one role review source field set drifted")
            role = review.get("selected_reference_role")
            review_id = review.get("review_id")
            decision = review.get("expected_decision")
            if role != expected_roles[role_ordinal] or type(review_id) is not str:
                _fail("one selected role differs from the frozen purpose order")
            if _EXPECTED_DECISIONS.get(review_id) != decision:
                _fail("one source expected decision differs from the frozen review plan")
            _bounded_text(review.get("request_basis"), label="request_basis")
            _bounded_text(review.get("decision_basis"), label="decision_basis")
            human = review.get("human_gate_results")
            if type(human) is not list or len(human) != 3:
                _fail("one role review must carry exactly three Checker findings")
            human_results: list[str] = []
            for gate_ordinal, raw_gate in enumerate(cast(list[object], human)):
                if type(raw_gate) is not dict:
                    _fail("human gate source entries must be exact objects")
                gate = cast(dict[str, object], raw_gate)
                if set(gate) != {"basis", "gate", "result"} or gate.get(
                    "gate"
                ) != _HUMAN_GATE_ORDER[gate_ordinal]:
                    _fail("human gate order drifted")
                result = gate.get("result")
                if result not in {"PASS", "FAIL", "INDETERMINATE"}:
                    _fail("human gate result is outside the exact closed vocabulary")
                _bounded_text(gate.get("basis"), label="human gate basis")
                human_results.append(result)
            derived_decision = (
                "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
                if "FAIL" in human_results
                else (
                    "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
                    if "INDETERMINATE" in human_results
                    else "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
                )
            )
            if derived_decision != decision:
                _fail("source decision is not the exact derivation from its Checker findings")
            observed_roles.append(role)
            observed_decisions.add(decision)
        typed_cases.append(case)
    if tuple(observed_roles) != tuple(role for roles in _ROLE_ORDER.values() for role in roles):
        _fail("reviewed source does not cover all seven roles in canonical purpose order")
    if observed_decisions != {
        "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
        "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
        "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
    }:
        _fail("reviewed source must cover positive, rejected and indeterminate decisions")
    return tuple(typed_cases)


@dataclass(frozen=True, slots=True)
class _ProtectedInputs:
    reviewed_source_raw: bytes
    reviewed_source: dict[str, object]
    old_fixture_raws: tuple[tuple[str, bytes], ...]

    def raw(self, relative_path: str) -> bytes:
        for path, raw in self.old_fixture_raws:
            if path == relative_path:
                return raw
        _fail("requested path is outside the exact eighteen-fixture upstream inventory")


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    protected: _ProtectedInputs
    derived_value: dict[str, object]
    derived_raw: bytes


@dataclass(frozen=True, slots=True)
class _PromotionKnownAnswerMaterials:
    materials: promotion_codegen._KnownAnswerMaterials
    request: promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1
    result: promotion_module.GeneratedReferenceAssetPromotionFinalizationResult
    maker_identity_bytes: bytes
    maker_action_bytes: bytes
    checker_identity_bytes: bytes
    checker_action_bytes: bytes
    promotion_at: str
    primary_sidecar_association_result: promotion_module.GateResult
    primary_sidecar_association_basis: str
    composite_unsplit_role_deferral_result: promotion_module.GateResult
    composite_unsplit_role_deferral_basis: str
    promotion_basis: str


@dataclass(frozen=True, slots=True)
class _RoleKnownAnswerMaterials:
    promotion: role_module.GeneratedReferenceRoleBindingPromotionClosureInput
    admitted_png: role_module.GeneratedReferenceRoleBindingAdmittedPng
    primary: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1
    maker_identity_bytes: bytes
    checker_identity_bytes: bytes


def _promotion_protected_inputs(
    protected: _ProtectedInputs,
) -> promotion_codegen._ProtectedInputs:
    source_raw = protected.raw(_PROMOTION_SOURCE_PATH)
    return promotion_codegen._ProtectedInputs(
        reviewed_source_raw=source_raw,
        reviewed_source=_parse_canonical_document(
            source_raw,
            label="frozen ADR-045 reviewed source fixture",
        ),
        old_fixture_raws=tuple(
            (path, protected.raw(path))
            for path in promotion_codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
        ),
    )


def _promotion_materials(
    protected: _ProtectedInputs,
    promotion_case_id: str,
) -> _PromotionKnownAnswerMaterials:
    promotion_protected = _promotion_protected_inputs(protected)
    promotion_cases = promotion_codegen._assert_source_shape(
        promotion_protected.reviewed_source
    )
    matching = [case for case in promotion_cases if case["case_id"] == promotion_case_id]
    if len(matching) != 1:
        _fail("reviewed Role-Binding case does not select one exact ADR-045 case")
    case = matching[0]
    materials = (
        promotion_codegen._character_materials(promotion_protected, case)
        if promotion_case_id == _PROMOTION_CASE_IDS[0]
        else promotion_codegen._scene_materials(promotion_protected, case)
    )
    source = cast(dict[str, object], case["promotion"])
    requested_at = cast(str, source["requested_at"])
    promotion_at = cast(str, source["promotion_at"])
    request_basis = cast(str, source["request_basis"])
    promotion_basis = cast(str, source["promotion_basis"])
    maker_identity = _canonical_document_bytes(source["maker_identity_record"])
    checker_identity = _canonical_document_bytes(source["checker_identity_record"])
    primary = promotion_module.build_generated_reference_promotion_primary_asset_binding(
        materials.primary_bible,
        materials.primary_asset_version,
    )
    _review_projection, review_sha = promotion_codegen._request_review_payload(
        materials=materials,
        binding=primary,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    maker_action = _canonical_document_bytes(
        {
            "action": "PREPARED_GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST",
            "actor_ref_sha256": _raw_sha256(maker_identity),
            "candidate_sha256": materials.upstream.candidate.candidate_sha256,
            "document_profile": (
                "sdc.generated-reference-asset-promotion-request-preparation-action.v1"
            ),
            "manifest_sha256": materials.upstream.manifest.manifest_sha256,
            "policy_document_sha256": (
                promotion_module.GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
            ),
            "promotion_review_payload_sha256": review_sha,
            "requested_at": requested_at,
            "requested_primary_asset_binding_sha256": primary.primary_asset_binding_sha256,
            "requested_status_receipt_sha256": materials.request_status.receipt.receipt_sha256,
        }
    )
    request = promotion_module.prepare_generated_reference_asset_promotion_request(
        materials.upstream,
        materials.request_status,
        materials.primary_bible,
        materials.primary_asset_version,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    gates = promotion_codegen._promotion_gate_results(source)
    checker_action = _canonical_document_bytes(
        {
            "action": "RECORDED_GENERATED_REFERENCE_ASSET_PROMOTION_DECISION",
            "actor_ref_sha256": _raw_sha256(checker_identity),
            "decision": "APPROVE_ELIGIBLE_ASSET_SIDECAR",
            "document_profile": "sdc.generated-reference-asset-promotion-decision-action.v1",
            "gate_results": [promotion_codegen._gate_projection(item) for item in gates],
            "policy_document_sha256": (
                promotion_module.GENERATED_REFERENCE_ASSET_PROMOTION_POLICY_DOCUMENT_SHA256
            ),
            "promotion_at": promotion_at,
            "promotion_basis": promotion_basis,
            "promotion_issue_codes": [],
            "promotion_primary_asset_binding_sha256": primary.primary_asset_binding_sha256,
            "promotion_status_receipt_sha256": materials.final_status.receipt.receipt_sha256,
            "request_sha256": request.request_sha256,
            "sidecar_materialization_allowed": True,
        }
    )
    human_by_gate = {
        cast(str, cast(dict[str, object], item)["gate"]): cast(dict[str, object], item)
        for item in cast(list[object], source["human_gate_results"])
    }
    association_basis = cast(
        str,
        human_by_gate["HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED"]["basis"],
    )
    deferral_basis = cast(
        str,
        human_by_gate["HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED"]["basis"],
    )
    result = promotion_module.finalize_generated_reference_asset_promotion(
        request,
        materials.upstream,
        materials.request_status,
        materials.primary_bible,
        materials.primary_asset_version,
        materials.final_status,
        materials.primary_bible,
        materials.primary_asset_version,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
        promotion_at=promotion_at,
        primary_sidecar_association_result="PASS",
        primary_sidecar_association_basis=association_basis,
        composite_unsplit_role_deferral_result="PASS",
        composite_unsplit_role_deferral_basis=deferral_basis,
        promotion_basis=promotion_basis,
    )
    if result.sidecar is None:
        _fail("frozen ADR-045 positive case did not atomically return its Sidecar")
    return _PromotionKnownAnswerMaterials(
        materials=materials,
        request=request,
        result=result,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
        promotion_at=promotion_at,
        primary_sidecar_association_result="PASS",
        primary_sidecar_association_basis=association_basis,
        composite_unsplit_role_deferral_result="PASS",
        composite_unsplit_role_deferral_basis=deferral_basis,
        promotion_basis=promotion_basis,
    )


def _role_materials(
    root: Path,
    protected: _ProtectedInputs,
    case: dict[str, object],
) -> _RoleKnownAnswerMaterials:
    promotion_known_answer = _promotion_materials(
        protected,
        cast(str, case["promotion_case_id"]),
    )
    promotion = role_module.GeneratedReferenceRoleBindingPromotionClosureInput(
        request=promotion_known_answer.request,
        result=promotion_known_answer.result,
        upstream=promotion_known_answer.materials.upstream,
        request_status=promotion_known_answer.materials.request_status,
        requested_primary_bible=promotion_known_answer.materials.primary_bible,
        requested_primary_asset_version=(
            promotion_known_answer.materials.primary_asset_version
        ),
        final_status=promotion_known_answer.materials.final_status,
        promotion_primary_bible=promotion_known_answer.materials.primary_bible,
        promotion_primary_asset_version=(
            promotion_known_answer.materials.primary_asset_version
        ),
        maker_identity_bytes=promotion_known_answer.maker_identity_bytes,
        maker_action_bytes=promotion_known_answer.maker_action_bytes,
        checker_identity_bytes=promotion_known_answer.checker_identity_bytes,
        checker_action_bytes=promotion_known_answer.checker_action_bytes,
        promotion_at=promotion_known_answer.promotion_at,
        primary_sidecar_association_result=(
            promotion_known_answer.primary_sidecar_association_result
        ),
        primary_sidecar_association_basis=(
            promotion_known_answer.primary_sidecar_association_basis
        ),
        composite_unsplit_role_deferral_result=(
            promotion_known_answer.composite_unsplit_role_deferral_result
        ),
        composite_unsplit_role_deferral_basis=(
            promotion_known_answer.composite_unsplit_role_deferral_basis
        ),
        promotion_basis=promotion_known_answer.promotion_basis,
    )
    png_relative_path = (
        promotion_codegen._CHARACTER_PNG_PATH
        if case["asset_purpose"] == "CHARACTER_REFERENCE_ASSET"
        else promotion_codegen._SCENE_PNG_PATH
    )
    admitted_png = role_module.admit_generated_reference_role_binding_png(
        _safe_path(root, png_relative_path, label="frozen role-binding PNG")
    )
    if admitted_png.png_bytes != protected.raw(png_relative_path):
        _fail("role-binding PNG admission differs from the frozen upstream bytes")
    primary = promotion_module.build_generated_reference_promotion_primary_asset_binding(
        promotion_known_answer.materials.primary_bible,
        promotion_known_answer.materials.primary_asset_version,
    )
    return _RoleKnownAnswerMaterials(
        promotion=promotion,
        admitted_png=admitted_png,
        primary=primary,
        maker_identity_bytes=_canonical_document_bytes(case["maker_identity_record"]),
        checker_identity_bytes=_canonical_document_bytes(case["checker_identity_record"]),
    )


_ROLE_COMPILER_GATE_BASES = (
    "COMPILER_REVALIDATED_EXACT_POSITIVE_PROMOTION_AND_ELIGIBLE_ASSET_SIDECAR",
    "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
    "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
    "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_ROLE_BINDING",
    "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
    "COMPILER_REVALIDATED_ROLE_PURPOSE_AND_PROFILE_MEMBERSHIP",
    "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
    None,
    None,
    None,
    "COMPILER_REVALIDATED_ROLE_BINDING_REVIEWER_SEPARATION",
)


def _role_gate_results(
    review: dict[str, object],
) -> tuple[role_module.GeneratedReferenceRoleBindingGateResultV1, ...]:
    human = cast(list[dict[str, object]], review["human_gate_results"])
    human_by_gate = {cast(str, item["gate"]): item for item in human}
    results = (
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        "PASS",
        human_by_gate[_HUMAN_GATE_ORDER[0]]["result"],
        human_by_gate[_HUMAN_GATE_ORDER[1]]["result"],
        human_by_gate[_HUMAN_GATE_ORDER[2]]["result"],
        "PASS",
    )
    bases = (
        _ROLE_COMPILER_GATE_BASES[0],
        _ROLE_COMPILER_GATE_BASES[1],
        _ROLE_COMPILER_GATE_BASES[2],
        _ROLE_COMPILER_GATE_BASES[3],
        _ROLE_COMPILER_GATE_BASES[4],
        _ROLE_COMPILER_GATE_BASES[5],
        _ROLE_COMPILER_GATE_BASES[6],
        _ROLE_COMPILER_GATE_BASES[7],
        human_by_gate[_HUMAN_GATE_ORDER[0]]["basis"],
        human_by_gate[_HUMAN_GATE_ORDER[1]]["basis"],
        human_by_gate[_HUMAN_GATE_ORDER[2]]["basis"],
        _ROLE_COMPILER_GATE_BASES[11],
    )
    return tuple(
        role_module.GeneratedReferenceRoleBindingGateResultV1.model_validate(
            {
                "basis": bases[ordinal],
                "gate": gate,
                "ordinal": ordinal,
                "result": results[ordinal],
            }
        )
        for ordinal, gate in enumerate(role_module.ROLE_BINDING_GATE_ORDER)
    )


def _role_issues(
    gates: tuple[role_module.GeneratedReferenceRoleBindingGateResultV1, ...],
) -> tuple[role_module.BindingIssueCode, ...]:
    mappings: dict[int, role_module.BindingIssueCode] = {
        4: "STATUS_NOT_CURRENT_AT_ROLE_BINDING",
        5: "PRIMARY_BINDING_NO_LONGER_ACTIVE",
        8: "EXACT_ROLE_AND_REVIEWED_RIGHTS_SCOPE_PRESENTATION_NOT_ACKNOWLEDGED",
        9: "WHOLE_COMPOSITE_ROLE_SUITABILITY_NOT_APPROVED",
        10: "NON_EXCLUSIVE_NO_TRANSFORM_BOUNDARY_NOT_ACKNOWLEDGED",
    }
    return tuple(
        mappings[index]
        for index in (4, 5, 8, 9, 10)
        if gates[index].result == "FAIL"
    )


def _role_decision(
    gates: tuple[role_module.GeneratedReferenceRoleBindingGateResultV1, ...],
) -> role_module.BindingDecision:
    if any(item.result == "FAIL" for item in gates):
        return "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"
    if any(item.result == "INDETERMINATE" for item in gates):
        return "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING"
    return "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"


def _role_known_answer_case(
    case: dict[str, object],
    review: dict[str, object],
    materials: _RoleKnownAnswerMaterials,
) -> dict[str, object]:
    promotion = materials.promotion
    requested_at = promotion.promotion_at
    binding_at = promotion.promotion_at
    selected_role = cast(str, review["selected_reference_role"])
    target = role_module.build_generated_reference_eligible_asset_role_binding_target(
        promotion,
        materials.admitted_png,
        selected_reference_role=selected_role,
    )
    review_projection = (
        role_module.build_generated_reference_role_binding_review_payload_projection(
            target,
            promotion,
            promotion.final_status,
            materials.primary,
            requested_at=requested_at,
        )
    )
    review_sha = _semantic_sha256(
        role_module.GENERATED_REFERENCE_ROLE_BINDING_REVIEW_PAYLOAD_SHA256_DOMAIN,
        review_projection,
    )
    maker_action = _canonical_document_bytes(
        role_module.generated_reference_role_binding_maker_action_projection(
            actor_ref_sha256=_raw_sha256(materials.maker_identity_bytes),
            role_binding_review_payload_sha256=review_sha,
            target_sha256=target.target_sha256,
            selected_reference_role=selected_role,
            requested_primary_asset_binding_sha256=(
                materials.primary.primary_asset_binding_sha256
            ),
            requested_status_receipt_sha256=(
                promotion.final_status.receipt.receipt_sha256
            ),
            prepared_at=requested_at,
            request_basis=cast(str, review["request_basis"]),
        )
    )
    request = (
        role_module.prepare_generated_reference_eligible_asset_role_binding_request(
            promotion,
            promotion.final_status,
            promotion.promotion_primary_bible,
            promotion.promotion_primary_asset_version,
            materials.admitted_png,
            selected_reference_role=selected_role,
            maker_identity_bytes=materials.maker_identity_bytes,
            maker_action_bytes=maker_action,
            requested_at=requested_at,
            request_basis=cast(str, review["request_basis"]),
        )
    )
    gates = _role_gate_results(review)
    issues = _role_issues(gates)
    decision = _role_decision(gates)
    if decision != review["expected_decision"]:
        _fail("independent role-binding decision differs from reviewed expected decision")
    human = cast(list[dict[str, object]], review["human_gate_results"])
    checker_action = _canonical_document_bytes(
        role_module.generated_reference_role_binding_checker_action_projection(
            request_id=request.request_id,
            request_sha256=request.request_sha256,
            target_sha256=target.target_sha256,
            selected_reference_role=selected_role,
            final_status_receipt_sha256=(
                promotion.final_status.receipt.receipt_sha256
            ),
            final_primary_asset_binding_sha256=(
                materials.primary.primary_asset_binding_sha256
            ),
            actor_ref_sha256=_raw_sha256(materials.checker_identity_bytes),
            reviewed_at=binding_at,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
                promotion_module.GateResult, human[0]["result"]
            ),
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result=cast(
                promotion_module.GateResult, human[1]["result"]
            ),
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result=cast(
                promotion_module.GateResult, human[2]["result"]
            ),
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            gate_results=gates,
            binding_issue_codes=issues,
            decision_basis=cast(str, review["decision_basis"]),
            decision=decision,
            binding_materialization_allowed=(
                decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
            ),
        )
    )
    result = role_module.finalize_generated_reference_eligible_asset_role_binding(
        request,
        promotion,
        promotion.final_status,
        promotion.promotion_primary_bible,
        promotion.promotion_primary_asset_version,
        promotion.final_status,
        promotion.promotion_primary_bible,
        promotion.promotion_primary_asset_version,
        materials.admitted_png,
        selected_reference_role=selected_role,
        maker_identity_bytes=materials.maker_identity_bytes,
        maker_action_bytes=maker_action,
        checker_identity_bytes=materials.checker_identity_bytes,
        checker_action_bytes=checker_action,
        binding_at=binding_at,
        exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
            promotion_module.GateResult, human[0]["result"]
        ),
        exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
            str, human[0]["basis"]
        ),
        whole_composite_role_suitability_result=cast(
            promotion_module.GateResult, human[1]["result"]
        ),
        whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
        non_exclusive_no_transform_boundary_result=cast(
            promotion_module.GateResult, human[2]["result"]
        ),
        non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
        decision_basis=cast(str, review["decision_basis"]),
    )
    if review["review_id"] == "character-identity-sheet-positive-v1":
        role_module.verify_generated_reference_eligible_asset_role_binding_finalization(
            result,
            request,
            promotion,
            promotion.final_status,
            promotion.promotion_primary_bible,
            promotion.promotion_primary_asset_version,
            promotion.final_status,
            promotion.promotion_primary_bible,
            promotion.promotion_primary_asset_version,
            materials.admitted_png,
            selected_reference_role=selected_role,
            maker_identity_bytes=materials.maker_identity_bytes,
            maker_action_bytes=maker_action,
            checker_identity_bytes=materials.checker_identity_bytes,
            checker_action_bytes=checker_action,
            binding_at=binding_at,
            exact_role_and_reviewed_rights_scope_presented_without_expansion_result=cast(
                promotion_module.GateResult, human[0]["result"]
            ),
            exact_role_and_reviewed_rights_scope_presented_without_expansion_basis=cast(
                str, human[0]["basis"]
            ),
            whole_composite_role_suitability_result=cast(
                promotion_module.GateResult, human[1]["result"]
            ),
            whole_composite_role_suitability_basis=cast(str, human[1]["basis"]),
            non_exclusive_no_transform_boundary_result=cast(
                promotion_module.GateResult, human[2]["result"]
            ),
            non_exclusive_no_transform_boundary_basis=cast(str, human[2]["basis"]),
            decision_basis=cast(str, review["decision_basis"]),
        )
    binding = result.binding
    if (binding is not None) is not (
        decision == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
    ):
        _fail("known answer Decision/Binding atomicity differs from policy")
    request_document = role_module.generated_reference_role_binding_contract_document_bytes(
        request
    )
    decision_document = role_module.generated_reference_role_binding_contract_document_bytes(
        result.decision
    )
    binding_document = (
        role_module.generated_reference_role_binding_contract_document_bytes(binding)
        if binding is not None
        else None
    )
    return {
        "asset_purpose": case["asset_purpose"],
        "binding": promotion_codegen._explicit(binding) if binding is not None else None,
        "binding_document_sha256": (
            _raw_sha256(binding_document) if binding_document is not None else None
        ),
        "binding_materialized": binding is not None,
        "binding_projection": (
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_projection(
                binding
            )
            if binding is not None
            else None
        ),
        "binding_sha256": binding.binding_sha256 if binding is not None else None,
        "case_id": case["case_id"],
        "checker_action_sha256": _raw_sha256(checker_action),
        "decision": promotion_codegen._explicit(result.decision),
        "decision_disposition": decision,
        "decision_document_sha256": _raw_sha256(decision_document),
        "decision_projection": (
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_decision_projection(
                result.decision
            )
        ),
        "decision_sha256": result.decision.decision_sha256,
        "fresh_replay_transition_count": 2,
        "human_gate_results": review["human_gate_results"],
        "maker_action_sha256": _raw_sha256(maker_action),
        "non_exclusive_boundary": {
            "complete_role_set_asserted": False,
            "current_role_binding_asserted": False,
            "global_role_uniqueness_asserted": False,
            "role_binding_exclusivity_asserted": False,
            "supersedes_role_binding": False,
        },
        "prohibited_media_operations": ["CROP", "SPLIT", "PROVIDER_INPUT"],
        "request": promotion_codegen._explicit(request),
        "request_document_sha256": _raw_sha256(request_document),
        "request_projection": (
            role_module.creative_sample_generated_reference_eligible_asset_role_binding_request_projection(
                request
            )
        ),
        "request_sha256": request.request_sha256,
        "review_id": review["review_id"],
        "review_payload_projection": review_projection,
        "review_payload_sha256": review_sha,
        "selected_reference_role": selected_role,
        "status_plan": case["status_plan"],
        "target": promotion_codegen._explicit(target),
        "target_projection": role_module.generated_reference_role_binding_target_projection(
            target
        ),
        "target_sha256": target.target_sha256,
    }


def _load_protected_inputs(root: Path) -> _ProtectedInputs:
    _assert_fixed_paths()
    source_raw = _read_frozen(
        root,
        _REVIEWED_SOURCE_PATH,
        max_bytes=_MAX_SOURCE_BYTES,
        label="reviewed ADR-046 source fixture",
    )
    old_raws: list[tuple[str, bytes]] = []
    for relative_path in _FROZEN_OLD_FIXTURE_FINGERPRINTS:
        maximum = _MAX_PNG_BYTES if relative_path.endswith(".png") else _MAX_OLD_FIXTURE_BYTES
        old_raws.append(
            (
                relative_path,
                _read_frozen(
                    root,
                    relative_path,
                    max_bytes=maximum,
                    label=f"frozen old fixture {relative_path}",
                ),
            )
        )
    source = _parse_canonical_document(source_raw, label="reviewed ADR-046 source fixture")
    _assert_source_shape(source)
    return _ProtectedInputs(
        reviewed_source_raw=source_raw,
        reviewed_source=source,
        old_fixture_raws=tuple(old_raws),
    )


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    """Build and independently verify the complete fixed ADR-046 known-answer packet."""

    protected = _load_protected_inputs(root)
    cases = _assert_source_shape(protected.reviewed_source)
    review_cases: list[dict[str, object]] = []
    for case in cases:
        materials = _role_materials(root, protected, case)
        review_cases.extend(
            _role_known_answer_case(case, cast(dict[str, object], review), materials)
            for review in cast(list[object], case["role_reviews"])
        )
    derived_value: dict[str, object] = {
        "boundary_checks": protected.reviewed_source["boundary_checks"],
        "cases": review_cases,
        "known_answer_version": _KNOWN_ANSWER_VERSION,
        "policy_document_sha256": _POLICY_DOCUMENT_SHA256,
        "reviewed_source": {
            "path": _REVIEWED_SOURCE_PATH,
            "raw_sha256": _raw_sha256(protected.reviewed_source_raw),
            "size_bytes": len(protected.reviewed_source_raw),
        },
        "upstream_inputs": [
            {
                "path": path,
                "raw_sha256": _raw_sha256(raw),
                "size_bytes": len(raw),
            }
            for path, raw in protected.old_fixture_raws
        ],
        "zero_authority_claim": (
            "TECHNICAL_KNOWN_ANSWER_ONLY_NO_RIGHTS_CURRENTNESS_PROVIDER_INPUT_OR_EXECUTION_AUTHORITY"
        ),
    }
    raw = _canonical_document_bytes(derived_value)
    if not 1 <= len(raw) <= _MAX_DERIVED_BYTES:
        _fail("derived known-answer fixture exceeds its fixed byte boundary")
    return _ExpectedClosure(
        protected=protected,
        derived_value=derived_value,
        derived_raw=raw,
    )


def _protected_file_infos(root: Path) -> tuple[os.stat_result, ...]:
    infos: list[os.stat_result] = []
    for relative_path in _PROTECTED_FINGERPRINTS:
        path = _safe_path(root, relative_path, label="protected input")
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise GeneratedReferenceRoleBindingCodegenError(
                "a protected input could not be inspected before update"
            ) from exc
        if not _is_regular_single_file(info):
            _fail("each protected input must remain one regular single-link file")
        infos.append(info)
    return tuple(infos)


def _write_exact_derived(root: Path, relative_path: str, raw: bytes) -> None:
    if relative_path != _DERIVED_FIXTURE_PATH:
        _fail("update attempted to write outside the single fixed derived-fixture allowlist")
    if type(raw) is not bytes or not 1 <= len(raw) <= _MAX_DERIVED_BYTES:
        _fail("derived fixture write bytes are outside the fixed boundary")
    _parse_canonical_document(raw, label="derived known-answer write bytes")
    destination = _safe_path(root, relative_path, label="derived known-answer fixture")
    protected_infos = _protected_file_infos(root)
    try:
        before = os.lstat(destination)
    except FileNotFoundError:
        before = None
    except OSError as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            "derived fixture destination could not be inspected"
        ) from exc
    if before is not None and not _is_regular_single_file(before):
        _fail("derived fixture destination must be one regular single-link file")
    flags = os.O_RDWR | os.O_CREAT
    binary_flag = getattr(os, "O_BINARY", 0)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if type(binary_flag) is int:
        flags |= binary_flag
    if type(no_follow) is int:
        flags |= no_follow
    descriptor: int | None = None
    try:
        descriptor = os.open(destination, flags, 0o644)
        opened = os.fstat(descriptor)
        if not _is_regular_single_file(opened):
            _fail("opened derived fixture is not one regular single-link file")
        if before is not None and not _same_file(before, opened):
            _fail("derived fixture destination changed before open")
        if any(_same_file(info, opened) for info in protected_infos):
            _fail("derived fixture aliases a protected source or old fixture")
        os.ftruncate(descriptor, 0)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("derived fixture write made no progress")
            offset += written
        os.fsync(descriptor)
        after_handle = os.fstat(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        remaining = len(raw) + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        actual = b"".join(chunks)
        after_path = os.lstat(destination)
        if (
            not _is_regular_single_file(after_handle)
            or not _is_regular_single_file(after_path)
            or not _same_file(after_handle, after_path)
            or len(actual) != len(raw)
            or actual != raw
        ):
            _fail("derived fixture changed during its direct guarded write")
    except GeneratedReferenceRoleBindingCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            "derived fixture could not be written directly"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    path = _safe_path(root, _DERIVED_FIXTURE_PATH, label="derived known-answer fixture")
    actual = _read_stable_regular_file(
        path,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    _parse_canonical_document(actual, label="derived known-answer fixture")
    if actual != closure.derived_raw:
        _fail("derived known-answer fixture is byte-stale")


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    before = _load_protected_inputs(root)
    if before != closure.protected:
        _fail("a protected input changed before derived-fixture update")
    _write_exact_derived(root, _DERIVED_FIXTURE_PATH, closure.derived_raw)
    after = _load_protected_inputs(root)
    if after != closure.protected:
        _fail("a protected input changed during derived-fixture update")
    _check_closure(root, closure)


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_parent = root / "src" / "sdc"
    if module_path.parent != expected_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    promotion_path = expected_parent / "generated_reference_asset_promotion_codegen.py"
    if Path(promotion_codegen.__file__).resolve() != promotion_path.resolve():
        _fail("upstream Promotion codegen does not belong to the same repository layout")
    pyproject = _safe_path(root, "pyproject.toml", label="repository pyproject.toml")
    raw = _read_stable_regular_file(
        pyproject,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GeneratedReferenceRoleBindingCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -B -m sdc.generated_reference_role_binding_codegen",
        description="Check or explicitly update the fixed ADR-046 known-answer fixture.",
        allow_abbrev=False,
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--update", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    root = _repository_root()
    closure = _build_expected_closure(root)
    if args.check:
        _check_closure(root, closure)
    elif args.update:
        _update_closure(root, closure)
    else:  # pragma: no cover
        _fail("one explicit codegen mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
