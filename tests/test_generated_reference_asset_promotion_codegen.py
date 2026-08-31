from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import cast

import pytest

import sdc.generated_reference_asset_promotion_codegen as codegen
import sdc.generated_reference_rights_current_status as rights

ROOT = Path(__file__).parents[1]


def _raw(relative_path: str) -> bytes:
    return (ROOT / relative_path).read_bytes()


def _source_is_frozen() -> bool:
    size, digest = codegen._REVIEWED_SOURCE_FINGERPRINT
    return size > 0 and len(digest) == 64 and (ROOT / codegen._REVIEWED_SOURCE_PATH).is_file()


def _materialize_protected_tree(root: Path) -> None:
    for relative_path in codegen._PROTECTED_FINGERPRINTS:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        source = ROOT / relative_path
        target.write_bytes(source.read_bytes() if source.is_file() else b"{}\n")


def _scope() -> dict[str, object]:
    return {
        "asset_promotion_authority_granted": False,
        "automated_execution_allowed": False,
        "commercial_use_rights_proven": False,
        "content_origin": "FIRST_PARTY_SYNTHETIC_TEST_CONTENT",
        "generation_authorized": False,
        "identity_authentication_claimed": False,
        "network_allowed": False,
        "provider_input_allowed": False,
        "provider_requests": 0,
        "publication_allowed": False,
        "purpose": "Offline deterministic SDC-ADR-045 promotion known-answer review only",
        "real_world_currentness_asserted": False,
        "real_world_eligibility_asserted": False,
        "retention_allowed": False,
        "role_binding_authorized": False,
        "training_allowed": False,
    }


def _identity(role: str) -> dict[str, object]:
    return {
        "document_profile": "sdc.privacy-minimized-human-reference.v1",
        "identity_namespace": "sdc.synthetic-adr045-test",
        "identity_ref": role.casefold().replace("_", "-"),
    }


def _promotion(case_id: str) -> dict[str, object]:
    return {
        "checker_identity_record": _identity(f"{case_id}-promotion-checker"),
        "decision": "APPROVE_ELIGIBLE_ASSET_SIDECAR",
        "human_gate_results": [
            {
                "basis": (
                    "Synthetic primary and Sidecar association is approved for this fixed test."
                ),
                "gate": "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
                "result": "PASS",
            },
            {
                "basis": "Synthetic composite remains unsplit and role assignment stays deferred.",
                "gate": "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED",
                "result": "PASS",
            },
        ],
        "maker_identity_record": _identity(f"{case_id}-promotion-maker"),
        "promotion_at": "2026-08-03T16:00:00Z",
        "promotion_basis": "First-party synthetic positive Promotion known answer only.",
        "request_basis": "Prepare one first-party synthetic Promotion review packet only.",
        "requested_at": "2026-08-03T15:00:00Z",
        "sidecar_materialization_allowed": True,
    }


def _primary(case_id: str) -> dict[str, object]:
    if case_id == codegen._CASE_IDS[0]:
        source_case = "character-reference-basic"
        asset_id = "character_asset_3087686f6e50d9cdcf1c"
        content_sha = "ee75137f45903e71783f4a67caa97b1373ce7f5b47e6f422508bef88be86f77d"
    else:
        source_case = "scene-reference-basic-empty-props"
        asset_id = "scene_asset_56f69f399a1e9fd2f482"
        content_sha = "4ba7559edf922ba6ca29accb1239e6232138ebcd55e7ea86465862e227c4adfc"
    return {
        "case_id": source_case,
        "expected_asset_version_id": asset_id,
        "expected_content_sha256": content_sha,
        "fixture_path": codegen._PRIMARY_ASSET_SOURCE_PATH,
    }


def _upstream(case_id: str) -> dict[str, object]:
    character = case_id == codegen._CASE_IDS[0]
    result: dict[str, object] = {
        "artifact_sha256": "1" * 64,
        "candidate_case_id": "character-reference-pass" if character else "scene-reference-pass",
        "candidate_generated_fixture_path": codegen._CANDIDATE_GENERATED_PATH,
        "candidate_id": "synthetic-candidate",
        "candidate_sha256": "2" * 64,
        "candidate_source_fixture_path": codegen._CANDIDATE_SOURCE_PATH,
        "media_content_sha256": "3" * 64,
        "media_size_bytes": 123,
        "png_path": codegen._CHARACTER_PNG_PATH if character else codegen._SCENE_PNG_PATH,
        "provider_attempt_outcome_id": "synthetic-outcome",
        "provider_attempt_outcome_sha256": "4" * 64,
        "subject_id": "synthetic-subject",
    }
    if character:
        result.update(
            {
                "rights_case_id": "character-reference-current-v1",
                "rights_generated_fixture_path": codegen._RIGHTS_GENERATED_PATH,
                "rights_source_fixture_path": codegen._RIGHTS_SOURCE_PATH,
            }
        )
    return result


def _observation(
    *,
    key: str,
    category: str,
    target: bool,
    link_kind: str = "GENESIS",
    predecessors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "basis_code": (
            "NO_EFFECTIVE_REVOCATION"
            if category == "REVOCATION_EFFECTIVE"
            else "RIGHTS_SCOPE_CONFIRMED"
        ),
        "basis_note": f"First-party synthetic {key} observation.",
        "category": category,
        "claim_value": (
            "ABSENT_WITH_EVIDENCE"
            if category in rights.CURRENT_STATUS_CATEGORY_ORDER[:4]
            else "PRESENT"
        ),
        "link_kind": link_kind,
        "observation_key": key,
        "observed_at": "2026-08-03T14:00:00Z",
        "predecessor_observation_keys": predecessors or [],
        "source_event_at": "2026-08-03T13:30:00Z",
        "source_kind": "RIGHTS_REVIEW_RECORD",
        "source_object": {"record_id": f"record-{key}", "synthetic": True},
        "source_object_media_type": "application/json",
        "source_object_ref": f"source-{key}",
        "source_reference": {
            "document_profile": "sdc.synthetic-current-status-source.v1",
            "source_id": f"source-{key}",
        },
        "target": target,
        "valid_from": "2026-08-03T13:30:00Z",
        "valid_until": "2026-08-04T10:00:00Z",
    }


def _status_source(*, final: bool) -> dict[str, object]:
    rights_source = json.loads(_raw(codegen._RIGHTS_SOURCE_PATH))
    rights_case = cast(dict[str, object], rights_source["positive_cases"][0])
    current_status = cast(dict[str, object], rights_case["current_status"])
    observations: list[dict[str, object]] = []
    for index, raw in enumerate(cast(list[dict[str, object]], current_status["observations"])):
        observation = copy.deepcopy(raw)
        observation["observation_key"] = f"scene-request-genesis-{index}"
        observation["source_event_at"] = f"2026-08-03T12:{10 + index:02d}:00Z"
        observation["observed_at"] = f"2026-08-03T12:{20 + index:02d}:00Z"
        observation["valid_from"] = "2026-08-03T12:00:00Z"
        observation["valid_until"] = "2026-08-04T10:00:00Z"
        observation["source_object_ref"] = f"sdc.synthetic-scene-source-object-{index}.v1"
        source_object = cast(dict[str, object], observation["source_object"])
        source_object["record_id"] = f"sdc.synthetic-scene-source-record-{index}.v1"
        source_object["subject_scope"] = codegen._CASE_IDS[1]
        source_reference = cast(dict[str, object], observation["source_reference"])
        source_reference["source_identity_ref"] = f"scene-source-{index}.v1"
        observation["predecessor_observation_keys"] = []
        observation["target"] = True
        observations.append(observation)
    if final:
        observations[0] = {**observations[0], "target": False}
        additions: tuple[tuple[str, str, list[str], bool], ...] = (
            ("scene-independent-new-target", "GENESIS", [], True),
            ("scene-successor-left", "SUCCESSOR", ["scene-request-genesis-0"], False),
            ("scene-successor-right", "SUCCESSOR", ["scene-request-genesis-0"], False),
            (
                "scene-reconciliation-target",
                "RECONCILIATION",
                ["scene-successor-left", "scene-successor-right"],
                True,
            ),
        )
        for offset, (key, link_kind, predecessors, target) in enumerate(additions):
            observation = copy.deepcopy(observations[0])
            observation.update(
                {
                    "link_kind": link_kind,
                    "observation_key": key,
                    "observed_at": f"2026-08-03T12:{40 + offset:02d}:00Z",
                    "predecessor_observation_keys": predecessors,
                    "source_event_at": f"2026-08-03T12:{30 + offset:02d}:00Z",
                    "source_object_ref": f"sdc.synthetic-{key}-object.v1",
                    "target": target,
                }
            )
            if link_kind == "SUCCESSOR":
                observation["basis_code"] = "HOLD_IMPOSED"
                observation["claim_value"] = "PRESENT"
            elif link_kind == "RECONCILIATION":
                observation["basis_code"] = "CONFLICT_IDENTIFIED"
                observation["claim_value"] = "CONFLICT"
                observation["valid_from"] = "2026-08-03T17:00:00Z"
            cast(dict[str, object], observation["source_object"])["record_id"] = (
                f"sdc.synthetic-{key}-record.v1"
            )
            observations.append(observation)
    return {
        "as_of": "2026-08-03T16:00:00Z" if final else "2026-08-03T15:00:00Z",
        "checker_basis": "Synthetic complete status check.",
        "checker_role": "FINAL_STATUS_CHECKER" if final else "REQUEST_STATUS_CHECKER",
        "evaluated_at": "2026-08-03T14:30:00Z" if final else "2026-08-03T14:00:00Z",
        "expected_as_of_status": "CURRENT",
        "expected_recorded_status": "CURRENT",
        "expected_request_valid_until": "2026-08-04T10:00:00Z",
        "expected_status_valid_until": "2026-08-04T10:00:00Z",
        "limitation_codes": list(rights.CURRENT_STATUS_LIMITATION_CODE_ORDER),
        "observations": observations,
        "preparer_role": "FINAL_STATUS_PREPARER" if final else "REQUEST_STATUS_PREPARER",
        "request_basis": "Synthetic complete finite target set.",
        "requested_at": "2026-08-03T13:30:00Z" if final else "2026-08-03T13:00:00Z",
    }


def _scene_source() -> dict[str, object]:
    candidate_source = json.loads(_raw(codegen._CANDIDATE_SOURCE_PATH))
    candidate_case = next(
        item for item in candidate_source["cases"] if item["case_id"] == "scene-reference-pass"
    )
    rights_source = json.loads(_raw(codegen._RIGHTS_SOURCE_PATH))
    rights_case = cast(dict[str, object], rights_source["positive_cases"][0])
    manifest = copy.deepcopy(cast(dict[str, object], rights_case["manifest"]))
    manifest["manifest_at"] = "2026-08-03T12:00:00Z"
    manifest["expected_manifest_valid_until"] = "2026-08-04T10:00:00Z"
    proposed = cast(dict[str, object], manifest["proposed_rights_scope"])
    proposed["proposed_scope_valid_until"] = "2026-08-04T10:00:00Z"
    reviewed = cast(dict[str, object], manifest["reviewed_rights_scope"])
    reviewed["reviewed_scope_valid_until"] = "2026-08-04T10:00:00Z"
    documents = cast(list[dict[str, object]], manifest["review_evidence_documents"])
    reviews = cast(list[dict[str, object]], manifest["human_gate_reviews"])
    for index, (document, review) in enumerate(zip(documents, reviews, strict=True)):
        record_id = cast(str, document["record_id"]).replace("character", "scene")
        document.update(
            {
                "effective_from": "2026-08-03T00:00:00Z",
                "effective_until": "2026-08-04T10:00:00Z",
                "evidence_valid_until": "2026-08-04T10:00:00Z",
                "observed_at": f"2026-08-03T11:{10 + index:02d}:00Z",
                "record_id": record_id,
            }
        )
        review["evidence_record_id"] = record_id
    roles = []
    for role in (
        "QUALIFICATION_QUALIFIER",
        "MANIFEST_MAKER",
        "MANIFEST_CHECKER",
        "REQUEST_STATUS_PREPARER",
        "REQUEST_STATUS_CHECKER",
        "FINAL_STATUS_PREPARER",
        "FINAL_STATUS_CHECKER",
    ):
        action: dict[str, object] = {"action": "SYNTHETIC_ACTION"}
        identity = _identity(role)
        if role == "QUALIFICATION_QUALIFIER":
            identity = copy.deepcopy(candidate_case["qualifier_reference"])
        elif role == "MANIFEST_MAKER":
            action = {
                "action": "PREPARED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
                "prepared_at": "2026-08-03T11:30:00Z",
            }
        elif role == "MANIFEST_CHECKER":
            action = {
                "action": "RECORDED_GENERATED_REFERENCE_RIGHTS_MANIFEST_REVIEW",
                "reviewed_at": "2026-08-03T12:00:00Z",
            }
        if role.endswith("PREPARER"):
            action = {
                "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
                "requested_at": (
                    "2026-08-03T13:30:00Z"
                    if role.startswith("FINAL")
                    else "2026-08-03T13:00:00Z"
                ),
            }
        elif role.endswith("CHECKER") and "MANIFEST" not in role:
            action = {
                "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
                "evaluated_at": (
                    "2026-08-03T14:30:00Z"
                    if role.startswith("FINAL")
                    else "2026-08-03T14:00:00Z"
                ),
            }
        roles.append(
            {
                "action_semantics": action,
                "identity_record": identity,
                "role": role,
            }
        )
    return {
        "manifest": manifest,
        "promotion_status": _status_source(final=True),
        "request_status": _status_source(final=False),
        "synthetic_role_records": roles,
    }


def _reviewed_source_shape() -> dict[str, object]:
    character_id, scene_id = codegen._CASE_IDS
    character = {
        "case_id": character_id,
        "primary_asset_source": _primary(character_id),
        "promotion": _promotion(character_id),
        "status_plan": "REUSE_ADR044_COMPLETE_RECORD_FOR_REQUEST_AND_PROMOTION_REPLAY",
        "upstream": _upstream(character_id),
    }
    scene = {
        "case_id": scene_id,
        "primary_asset_source": _primary(scene_id),
        "promotion": _promotion(scene_id),
        "scene_rights_current_status": _scene_source(),
        "status_plan": (
            "MONOTONIC_SUCCESSOR_RECONCILIATION_WITH_RECANONICALIZED_TARGET_ORDINALS"
        ),
        "upstream": _upstream(scene_id),
    }
    return {
        "cases": [character, scene],
        "known_answer_version": "1.0.0",
        "source_packet_scope": _scope(),
    }


def _frozen_protected_inputs() -> codegen._ProtectedInputs:
    reviewed_source: dict[str, object] = {
        "cases": [
            _character_case_from_frozen_inputs(),
            _scene_case_from_frozen_inputs(),
        ],
        "known_answer_version": "1.0.0",
        "source_packet_scope": _scope(),
    }
    return codegen._ProtectedInputs(
        reviewed_source_raw=codegen._canonical_document_bytes(reviewed_source),
        reviewed_source=reviewed_source,
        old_fixture_raws=tuple(
            (relative_path, _raw(relative_path))
            for relative_path in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
        ),
    )


def _character_case_from_frozen_inputs() -> dict[str, object]:
    generated = json.loads(_raw(codegen._RIGHTS_GENERATED_PATH))
    positive_case = cast(dict[str, object], generated["positive_cases"][0])
    artifact = cast(dict[str, object], positive_case["artifact"])
    outcome = cast(dict[str, object], positive_case["provider_attempt_outcome"])
    candidate = cast(dict[str, object], positive_case["candidate"])
    promotion = _promotion(codegen._CASE_IDS[0])
    promotion.update(
        {
            "promotion_at": "2026-08-29T06:00:00Z",
            "requested_at": "2026-08-29T05:00:00Z",
        }
    )
    upstream = _upstream(codegen._CASE_IDS[0])
    upstream.update(
        {
            "artifact_sha256": artifact["artifact_sha256"],
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "media_content_sha256": candidate["media_content_sha256"],
            "media_size_bytes": candidate["media_size_bytes"],
            "provider_attempt_outcome_id": outcome["outcome_id"],
            "provider_attempt_outcome_sha256": outcome["outcome_sha256"],
            "subject_id": candidate["subject_id"],
        }
    )
    return {
        "case_id": codegen._CASE_IDS[0],
        "primary_asset_source": _primary(codegen._CASE_IDS[0]),
        "promotion": promotion,
        "status_plan": "REUSE_ADR044_COMPLETE_RECORD_FOR_REQUEST_AND_PROMOTION_REPLAY",
        "upstream": upstream,
    }


def _scene_case_from_frozen_inputs() -> dict[str, object]:
    generated = json.loads(_raw(codegen._CANDIDATE_GENERATED_PATH))
    generated_case = next(
        item for item in generated["cases"] if item["case_id"] == "scene-reference-pass"
    )
    artifact = cast(dict[str, object], generated_case["artifact"])
    outcome = cast(dict[str, object], generated_case["provider_attempt_outcome"])
    candidate = cast(dict[str, object], generated_case["candidate"])
    upstream = _upstream(codegen._CASE_IDS[1])
    upstream.update(
        {
            "artifact_sha256": artifact["artifact_sha256"],
            "candidate_id": candidate["candidate_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "media_content_sha256": candidate["media_content_sha256"],
            "media_size_bytes": candidate["media_size_bytes"],
            "provider_attempt_outcome_id": outcome["outcome_id"],
            "provider_attempt_outcome_sha256": outcome["outcome_sha256"],
            "subject_id": candidate["subject_id"],
        }
    )
    return {
        "case_id": codegen._CASE_IDS[1],
        "primary_asset_source": _primary(codegen._CASE_IDS[1]),
        "promotion": _promotion(codegen._CASE_IDS[1]),
        "scene_rights_current_status": _scene_source(),
        "status_plan": (
            "MONOTONIC_SUCCESSOR_RECONCILIATION_WITH_RECANONICALIZED_TARGET_ORDINALS"
        ),
        "upstream": upstream,
    }
def test_all_sixteen_old_fixture_paths_and_bytes_are_frozen() -> None:
    assert len(codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS) == 16
    assert codegen._REVIEWED_SOURCE_PATH not in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    assert codegen._DERIVED_FIXTURE_PATH not in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    for relative_path, (size, digest) in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS.items():
        raw = _raw(relative_path)
        assert len(raw) == size
        assert hashlib.sha256(raw).hexdigest() == digest


def test_reviewed_source_anchor_fails_closed_until_separate_human_review() -> None:
    size, digest = codegen._REVIEWED_SOURCE_FINGERPRINT
    path = ROOT / codegen._REVIEWED_SOURCE_PATH
    if (size, digest) == (0, "SOURCE_REVIEW_REQUIRED"):
        if path.exists():
            with pytest.raises(ValueError, match="have not been frozen"):
                codegen._read_frozen(
                    ROOT,
                    codegen._REVIEWED_SOURCE_PATH,
                    max_bytes=codegen._MAX_SOURCE_BYTES,
                    label="reviewed source",
                )
        return
    assert path.is_file()
    assert size > 0
    assert len(digest) == 64
    raw = path.read_bytes()
    assert len(raw) == size
    assert hashlib.sha256(raw).hexdigest() == digest


def test_reviewed_source_shape_requires_two_bounded_zero_authority_cases() -> None:
    source = _reviewed_source_shape()
    cases = codegen._assert_source_shape(source)
    assert tuple(item["case_id"] for item in cases) == codegen._CASE_IDS
    scene = cases[1]
    scene_source = cast(dict[str, object], scene["scene_rights_current_status"])
    request_status = cast(dict[str, object], scene_source["request_status"])
    promotion_status = cast(dict[str, object], scene_source["promotion_status"])
    assert len(cast(list[object], request_status["observations"])) == 9
    assert len(cast(list[object], promotion_status["observations"])) == 13
    cast(dict[str, object], source["source_packet_scope"])["provider_requests"] = 1
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._assert_source_shape(source)


def test_persistent_parser_rejects_noncanonical_and_exact_resource_boundaries(
    tmp_path: Path,
) -> None:
    assert codegen._MAX_SOURCE_BYTES == 2_097_152
    assert codegen._MAX_DERIVED_BYTES == 4_194_304
    assert codegen._MAX_OLD_FIXTURE_BYTES == 4_194_304
    assert codegen._MAX_PNG_BYTES == 67_108_864
    assert codegen._MAX_REPOSITORY_METADATA_BYTES == 262_144
    assert codegen._MAX_JSON_CONTAINER_DEPTH == 24
    assert codegen._MAX_JSON_CONTAINER_ITEMS == 256
    canonical = codegen._canonical_document_bytes({"a": 1})
    assert codegen._parse_canonical_document(canonical, label="fixture") == {"a": 1}
    for raw in (
        b"",
        b'{"a":1}\n',
        b'{"a": 1}\r\n',
        b'\xef\xbb\xbf{"a": 1}\n',
        b'{"a": 1, "a": 2}\n',
        b'{"a": NaN}\n',
    ):
        with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
            codegen._parse_canonical_document(raw, label="fixture")
    depth_24: object = "leaf"
    for _ in range(24):
        depth_24 = [depth_24]
    assert codegen._canonical_document_bytes(depth_24)
    depth_25 = [depth_24]
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._canonical_document_bytes(depth_25)
    assert codegen._canonical_document_bytes(list(range(256)))
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._canonical_document_bytes(list(range(257)))
    zero = tmp_path / "zero.bin"
    maximum = tmp_path / "maximum.bin"
    over = tmp_path / "over.bin"
    zero.write_bytes(b"")
    maximum.write_bytes(b"x" * 8)
    over.write_bytes(b"x" * 9)
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._read_stable_regular_file(zero, max_bytes=8, label="zero")
    assert codegen._read_stable_regular_file(maximum, max_bytes=8, label="maximum") == (
        b"x" * 8
    )
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._read_stable_regular_file(over, max_bytes=8, label="over")


def test_stable_reader_rejects_symlink_hardlink_and_reparse_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ordinary = tmp_path / "ordinary.json"
    ordinary.write_bytes(b"{}\n")
    hardlink = tmp_path / "hardlink.json"
    try:
        os.link(ordinary, hardlink)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._read_stable_regular_file(ordinary, max_bytes=100, label="fixture")
    symlink = tmp_path / "symlink.json"
    try:
        symlink.symlink_to(hardlink)
    except OSError:
        pass
    else:
        with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
            codegen._read_stable_regular_file(symlink, max_bytes=100, label="fixture")
    info = os.lstat(hardlink)
    monkeypatch.setattr(
        os,
        "lstat",
        lambda path: type("ReparseStat", (), {
            "st_mode": info.st_mode,
            "st_file_attributes": codegen._WINDOWS_REPARSE_POINT_ATTRIBUTE,
        })(),
    )
    assert not codegen._is_regular_non_symlink(os.lstat(hardlink))


def test_fixture_path_rejects_escape_and_symlinked_ancestor(tmp_path: Path) -> None:
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._safe_path(tmp_path, "../outside.json", label="fixture")
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this host")
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._safe_path(tmp_path, "linked/value.json", label="fixture")


def test_writer_directly_writes_only_fixed_derived_target(tmp_path: Path) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    raw = codegen._canonical_document_bytes({"known_answer_version": "test"})
    codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, raw)
    assert derived.read_bytes() == raw
    with pytest.raises(
        codegen.GeneratedReferenceAssetPromotionCodegenError,
        match="single fixed derived-fixture allowlist",
    ):
        codegen._write_exact_derived(tmp_path, codegen._REVIEWED_SOURCE_PATH, raw)
    for relative_path in codegen._PROTECTED_FINGERPRINTS:
        expected = _raw(relative_path) if (ROOT / relative_path).is_file() else b"{}\n"
        assert (tmp_path / relative_path).read_bytes() == expected


def test_writer_rejects_hardlinked_symlinked_and_changed_destination(tmp_path: Path) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.parent.mkdir(parents=True, exist_ok=True)
    peer = tmp_path / "peer.json"
    peer.write_bytes(b"{}\n")
    try:
        os.link(peer, derived)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    raw = codegen._canonical_document_bytes({"value": 1})
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, raw)
    derived.unlink()
    try:
        derived.symlink_to(peer)
    except OSError:
        return
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, raw)


def test_writer_leaf_replacement_race_cannot_modify_victim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.parent.mkdir(parents=True, exist_ok=True)
    derived.write_bytes(codegen._canonical_document_bytes({"old": True}))
    victim = tmp_path / "leaf-race-victim.json"
    victim_bytes = b"DO NOT MODIFY LEAF VICTIM\n"
    victim.write_bytes(victim_bytes)
    parked = tmp_path / "parked-derived.json"
    original_safe_path = codegen._safe_path
    original_lstat = os.lstat
    original_stat = os.stat
    armed = False
    raced = False

    def arm_after_safe_path(root: Path, relative_path: str, *, label: str) -> Path:
        nonlocal armed
        result = original_safe_path(root, relative_path, label=label)
        if relative_path == codegen._DERIVED_FIXTURE_PATH:
            armed = True
        return result

    def replace_leaf_after_lstat(path: os.PathLike[str] | str) -> os.stat_result:
        nonlocal raced
        info = original_lstat(path)
        if armed and not raced and Path(path) == derived:
            raced = True
            os.replace(derived, parked)
            os.link(victim, derived)
        return info

    def replace_leaf_after_stat(
        path: os.PathLike[str] | str,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal raced
        info = original_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if armed and not raced and dir_fd is not None and str(path) == derived.name:
            raced = True
            os.replace(derived, parked)
            os.link(victim, derived)
        return info

    monkeypatch.setattr(codegen, "_safe_path", arm_after_safe_path)
    if sys.platform == "win32":
        monkeypatch.setattr(os, "lstat", replace_leaf_after_lstat)
    else:
        monkeypatch.setattr(
            os,
            "supports_dir_fd",
            {*os.supports_dir_fd, replace_leaf_after_stat},
        )
        monkeypatch.setattr(
            os,
            "supports_follow_symlinks",
            {*os.supports_follow_symlinks, replace_leaf_after_stat},
        )
        monkeypatch.setattr(os, "stat", replace_leaf_after_stat)
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._write_exact_derived(
            tmp_path,
            codegen._DERIVED_FIXTURE_PATH,
            codegen._canonical_document_bytes({"new": True}),
        )
    assert raced
    assert victim.read_bytes() == victim_bytes


def test_writer_ancestor_replacement_race_cannot_modify_victim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.parent.mkdir(parents=True, exist_ok=True)
    derived.write_bytes(codegen._canonical_document_bytes({"old": True}))
    victim = tmp_path / "ancestor-race-victim.json"
    victim_bytes = b"DO NOT MODIFY ANCESTOR VICTIM\n"
    victim.write_bytes(victim_bytes)
    parked_directory = tmp_path / "parked-promotion-directory"
    original_safe_path = codegen._safe_path
    original_lstat = os.lstat
    original_stat = os.stat
    armed = False
    raced = False

    def arm_after_safe_path(root: Path, relative_path: str, *, label: str) -> Path:
        nonlocal armed
        result = original_safe_path(root, relative_path, label=label)
        if relative_path == codegen._DERIVED_FIXTURE_PATH:
            armed = True
        return result

    def replace_directory() -> None:
        nonlocal raced
        raced = True
        os.replace(derived.parent, parked_directory)
        derived.parent.mkdir(parents=False)
        os.link(victim, derived)

    def windows_racing_lstat(path: os.PathLike[str] | str) -> os.stat_result:
        info = original_lstat(path)
        if armed and not raced and Path(path) == derived.parent:
            replace_directory()
        return info

    def posix_racing_stat(
        path: os.PathLike[str] | str,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        info = original_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if (
            armed
            and not raced
            and dir_fd is not None
            and str(path) == derived.parent.name
        ):
            replace_directory()
        return info

    monkeypatch.setattr(codegen, "_safe_path", arm_after_safe_path)
    if sys.platform == "win32":
        monkeypatch.setattr(os, "lstat", windows_racing_lstat)
    else:
        monkeypatch.setattr(
            os,
            "supports_dir_fd",
            {*os.supports_dir_fd, posix_racing_stat},
        )
        monkeypatch.setattr(
            os,
            "supports_follow_symlinks",
            {*os.supports_follow_symlinks, posix_racing_stat},
        )
        monkeypatch.setattr(os, "stat", posix_racing_stat)
    with pytest.raises(codegen.GeneratedReferenceAssetPromotionCodegenError):
        codegen._write_exact_derived(
            tmp_path,
            codegen._DERIVED_FIXTURE_PATH,
            codegen._canonical_document_bytes({"new": True}),
        )
    assert raced
    assert victim.read_bytes() == victim_bytes


def test_check_mode_has_no_reachable_write_path(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(codegen, "_build_expected_closure", lambda root: sentinel)
    observed: list[tuple[Path, object]] = []
    monkeypatch.setattr(
        codegen,
        "_check_closure",
        lambda root, closure: observed.append((root, closure)),
    )

    def fail_write(*args: object, **kwargs: object) -> None:
        raise AssertionError("--check reached a write path")

    monkeypatch.setattr(codegen, "_update_closure", fail_write)
    monkeypatch.setattr(codegen, "_write_exact_derived", fail_write)
    assert codegen.main(["--check"]) == 0
    assert observed == [(ROOT, sentinel)]


def test_real_closure_check_keeps_every_mutator_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protected = _frozen_protected_inputs()
    monkeypatch.setattr(codegen, "_load_protected_inputs", lambda root: protected)
    closure = codegen._build_expected_closure(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.parent.mkdir(parents=True)
    derived.write_bytes(closure.derived_raw)
    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    mutations: list[str] = []

    def reject_mutation(name: str) -> None:
        mutations.append(name)
        raise AssertionError(f"--check reached mutator {name}")

    def reject_call(name: str) -> object:
        def rejected(*args: object, **kwargs: object) -> None:
            reject_mutation(name)

        return rejected

    original_os_open = os.open
    write_open_mask = (
        os.O_WRONLY
        | os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | os.O_TRUNC
        | int(getattr(os, "O_APPEND", 0))
    )

    def read_only_os_open(
        path: os.PathLike[str] | str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if flags & write_open_mask:
            reject_mutation("os.open-write-flags")
        return original_os_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", read_only_os_open)
    monkeypatch.setattr(builtins, "open", reject_call("builtins.open"))
    for name in (
        "chmod",
        "chown",
        "fchmod",
        "fchown",
        "ftruncate",
        "lchown",
        "link",
        "makedirs",
        "mkdir",
        "pwrite",
        "pwritev",
        "remove",
        "removedirs",
        "rename",
        "renames",
        "replace",
        "rmdir",
        "symlink",
        "truncate",
        "unlink",
        "utime",
        "write",
        "writev",
    ):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, reject_call(f"os.{name}"))
    for name in (
        "chmod",
        "hardlink_to",
        "mkdir",
        "rename",
        "replace",
        "rmdir",
        "symlink_to",
        "touch",
        "unlink",
        "write_bytes",
        "write_text",
    ):
        monkeypatch.setattr(Path, name, reject_call(f"Path.{name}"))
    monkeypatch.setattr(codegen, "_write_exact_derived", reject_call("codegen writer"))
    monkeypatch.setattr(codegen, "_update_closure", reject_call("codegen update"))
    monkeypatch.setattr(
        codegen,
        "_acquire_windows_directory_guard",
        reject_call("Windows directory guard"),
    )
    assert codegen.main(["--check"]) == 0
    assert mutations == []


def test_cli_has_only_explicit_fixed_root_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = codegen._argument_parser()
    safe_program = "python -B -m sdc.generated_reference_asset_promotion_codegen"
    assert parser.prog == safe_program
    assert parser.allow_abbrev is False
    assert safe_program in parser.format_help()
    assert "python -m sdc.generated_reference_asset_promotion_codegen" not in parser.format_help()
    sentinel = object()
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(codegen, "_build_expected_closure", lambda root: sentinel)
    monkeypatch.setattr(codegen, "_check_closure", lambda root, closure: None)
    monkeypatch.setattr(codegen, "_update_closure", lambda root, closure: None)
    assert codegen.main(["--check"]) == 0
    assert codegen.main(["--update"]) == 0
    admissions: list[object] = []
    monkeypatch.setattr(codegen, "_repository_root", lambda: admissions.append(object()))
    for argv in (
        [],
        ["--check", "--update"],
        ["--root", str(ROOT)],
        ["--unknown"],
        ["--c"],
        ["--che"],
        ["--u"],
        ["--upd"],
    ):
        with pytest.raises(SystemExit):
            codegen.main(argv)
        assert admissions == []


def test_independent_projection_fields_and_six_domains_are_exact_and_disjoint() -> None:
    codegen._assert_projection_field_sets()
    domains = {
        codegen._REVIEW_PAYLOAD_DOMAIN,
        codegen._PRIMARY_ASSET_VERSION_DOMAIN,
        codegen._PRIMARY_BINDING_DOMAIN,
        codegen._REQUEST_DOMAIN,
        codegen._DECISION_DOMAIN,
        codegen._SIDECAR_DOMAIN,
    }
    assert len(domains) == 6
    assert all(value.endswith(b"\0") for value in domains)


def test_character_full_core_path_reuses_one_frozen_adr044_status_record() -> None:
    case = codegen._promotion_known_answer_case(
        _frozen_protected_inputs(),
        _character_case_from_frozen_inputs(),
    )
    request_record = cast(dict[str, object], case["request_status_record"])
    promotion_record = cast(dict[str, object], case["promotion_status_record"])
    assert request_record == promotion_record
    assert cast(dict[str, object], case["decision"])["decision"] == (
        "APPROVE_ELIGIBLE_ASSET_SIDECAR"
    )
    assert cast(dict[str, object], case["sidecar"])["promotion_performed"] is True


def test_character_rejects_one_field_drift_in_frozen_adr044_generated_closure() -> None:
    protected = _frozen_protected_inputs()
    generated = json.loads(protected.raw(codegen._RIGHTS_GENERATED_PATH))
    positive = cast(dict[str, object], generated["positive_cases"][0])
    assessment = cast(dict[str, object], positive["record_as_of_assessment"])
    assessment["status_valid_until"] = "2026-08-30T01:30:01Z"
    mutated_raw = codegen._canonical_document_bytes(generated)
    mutated = codegen._ProtectedInputs(
        reviewed_source_raw=protected.reviewed_source_raw,
        reviewed_source=protected.reviewed_source,
        old_fixture_raws=tuple(
            (path, mutated_raw if path == codegen._RIGHTS_GENERATED_PATH else raw)
            for path, raw in protected.old_fixture_raws
        ),
    )
    with pytest.raises(
        codegen.GeneratedReferenceAssetPromotionCodegenError,
        match="complete independent source rebuild",
    ):
        codegen._character_materials(
            mutated,
            _character_case_from_frozen_inputs(),
        )


def test_scene_full_core_path_reconciles_and_recanonicalizes_targets() -> None:
    case = codegen._promotion_known_answer_case(
        _frozen_protected_inputs(),
        _scene_case_from_frozen_inputs(),
    )
    request_topology = cast(dict[str, object], case["request_status_topology"])
    promotion_topology = cast(dict[str, object], case["promotion_status_topology"])
    request_targets = cast(list[dict[str, object]], request_topology["target_observation_refs"])
    promotion_targets = cast(
        list[dict[str, object]], promotion_topology["target_observation_refs"]
    )
    assert len(request_targets) == 9
    assert len(promotion_targets) == 10
    request_ordinals = {
        (item["observation_id"], item["observation_sha256"], item["chain_sha256"]): item[
            "ordinal"
        ]
        for item in request_targets
    }
    promotion_ordinals = {
        (item["observation_id"], item["observation_sha256"], item["chain_sha256"]): item[
            "ordinal"
        ]
        for item in promotion_targets
    }
    retained = request_ordinals.keys() & promotion_ordinals.keys()
    assert retained
    assert any(request_ordinals[key] != promotion_ordinals[key] for key in retained)


def test_codegen_has_one_persistence_exception_and_no_external_capability() -> None:
    source = Path(codegen.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "eval",
                "exec",
                "compile",
                "__import__",
            }:
                forbidden_calls.append(node.func.id)
    assert forbidden_calls == []
    assert not imported & {
        "asyncio",
        "httpx",
        "importlib",
        "requests",
        "secrets",
        "socket",
        "subprocess",
        "temporalio",
        "urllib",
    }
    folded = source.casefold()
    for marker in (
        "os.environ",
        "getenv(",
        "datetime.now(",
        "datetime.utcnow(",
        "time.time(",
        "random.",
        "uuid4(",
        "tempfile",
        "shutil",
    ):
        assert marker not in folded
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }

    def enclosing_scope(node: ast.AST) -> str:
        current = parents.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current.name
            current = parents.get(current)
        return "<module>"

    def qualified_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = qualified_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    persistent_names = {
        "os.chmod",
        "os.chown",
        "os.copy_file_range",
        "os.fchmod",
        "os.fchown",
        "os.fsync",
        "os.ftruncate",
        "os.lchown",
        "os.link",
        "os.makedirs",
        "os.mkfifo",
        "os.mkdir",
        "os.mknod",
        "os.posix_fallocate",
        "os.pwrite",
        "os.pwritev",
        "os.remove",
        "os.removexattr",
        "os.removedirs",
        "os.rename",
        "os.renames",
        "os.replace",
        "os.rmdir",
        "os.sendfile",
        "os.setxattr",
        "os.splice",
        "os.symlink",
        "os.truncate",
        "os.unlink",
        "os.utime",
        "os.write",
        "os.writev",
    }
    persistent_attributes = {
        "chmod",
        "hardlink_to",
        "lchmod",
        "link_to",
        "mkdir",
        "rename",
        "replace",
        "rmdir",
        "symlink_to",
        "touch",
        "truncate",
        "unlink",
        "write",
        "write_bytes",
        "write_text",
        "writelines",
    }
    persistent_calls: list[tuple[str, str]] = []
    generic_open_calls: list[tuple[str, str]] = []
    os_open_calls: list[tuple[str, ast.Call]] = []
    open_osfhandle_calls: list[str] = []
    windows_create_calls: list[tuple[str, ast.Call]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = qualified_name(node.func)
        scope = enclosing_scope(node)
        if name == "open":
            persistent_calls.append((scope, name))
        if (
            name in {"open", "io.open", "os.fdopen"}
            or (name.endswith(".open") and name != "os.open")
        ):
            generic_open_calls.append((scope, name))
        if name == "os.open":
            os_open_calls.append((scope, node))
        if name.endswith(".open_osfhandle"):
            open_osfhandle_calls.append(scope)
        if name == "create_file":
            windows_create_calls.append((scope, node))
        if name in persistent_names or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in persistent_attributes
            and not (node.func.attr == "replace" and scope == "_parse_utc")
        ):
            persistent_calls.append((scope, name))
    assert persistent_calls
    assert {scope for scope, _ in persistent_calls} == {"_write_exact_derived"}
    assert {name for _, name in persistent_calls} >= {"os.fsync", "os.ftruncate", "os.write"}
    assert generic_open_calls == []
    assert {scope for scope, _ in os_open_calls} == {
        "_read_stable_regular_file",
        "_write_exact_derived",
    }
    assert open_osfhandle_calls == ["_write_exact_derived"]
    assert [scope for scope, _ in windows_create_calls] == [
        "_acquire_windows_directory_guard",
        "_write_exact_derived",
    ]
    function_nodes = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    reader_source = ast.unparse(function_nodes["_read_stable_regular_file"])
    writer_source = ast.unparse(function_nodes["_write_exact_derived"])
    assert "os.O_RDONLY" in reader_source
    assert "O_NOFOLLOW" in reader_source
    assert all(
        marker not in reader_source
        for marker in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "os.O_TRUNC")
    )
    for marker in (
        "os.O_RDWR",
        "os.O_CREAT",
        "os.O_EXCL",
        "O_NOFOLLOW",
        "O_DIRECTORY",
        "O_CLOEXEC",
        "FILE_FLAG_OPEN_REPARSE_POINT",
    ):
        if marker == "FILE_FLAG_OPEN_REPARSE_POINT":
            assert "2097152" in writer_source
        else:
            assert marker in writer_source
    assert "os.O_TRUNC" not in writer_source
    for scope, call in windows_create_calls:
        integer_literals = {
            item.value
            for item in ast.walk(call)
            if isinstance(item, ast.Constant) and type(item.value) is int
        }
        assert 0x00200000 in integer_literals
        if scope == "_acquire_windows_directory_guard":
            assert 3 in integer_literals
        else:
            assert {1, 3} <= integer_literals


@pytest.mark.skipif(
    not _source_is_frozen(),
    reason="reviewed ADR-045 source bytes have not received their separate frozen anchor",
)
def test_complete_known_answer_closure_is_deterministic_and_checked_in() -> None:
    first = codegen._build_expected_closure(ROOT)
    second = codegen._build_expected_closure(ROOT)
    assert first.derived_raw == second.derived_raw
    assert first.derived_value == second.derived_value
    assert 1 <= len(first.derived_raw) <= codegen._MAX_DERIVED_BYTES
    cases = cast(list[dict[str, object]], first.derived_value["cases"])
    assert tuple(item["case_id"] for item in cases) == codegen._CASE_IDS
    for case in cases:
        assert cast(dict[str, object], case["decision"])["decision"] == (
            "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        )
        assert cast(dict[str, object], case["sidecar"])["promotion_performed"] is True
    actual = _raw(codegen._DERIVED_FIXTURE_PATH)
    assert actual == first.derived_raw
    assert codegen._parse_canonical_document(
        actual, label="derived known-answer fixture"
    ) == first.derived_value
