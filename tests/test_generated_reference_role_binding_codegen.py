from __future__ import annotations

import ast
import copy
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from sdc import generated_reference_role_binding as role_binding
from sdc import generated_reference_role_binding_codegen as codegen

ROOT = Path(__file__).resolve().parents[1]


def _raw(relative_path: str) -> bytes:
    return (ROOT / relative_path).read_bytes()


def _value(relative_path: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_raw(relative_path)))


@pytest.fixture(scope="module")
def expected_closure() -> codegen._ExpectedClosure:
    return codegen._build_expected_closure(ROOT)


def test_all_eighteen_pre_adr046_fixture_paths_and_bytes_are_frozen() -> None:
    assert len(codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS) == 18
    assert codegen._REVIEWED_SOURCE_PATH not in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    assert codegen._DERIVED_FIXTURE_PATH not in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    assert codegen._PROMOTION_SOURCE_PATH in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    assert codegen._PROMOTION_GENERATED_PATH in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    for relative_path, (size, digest) in codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS.items():
        raw = _raw(relative_path)
        assert len(raw) == size
        assert hashlib.sha256(raw).hexdigest() == digest


def test_reviewed_source_has_one_independent_fixed_byte_anchor() -> None:
    raw = _raw(codegen._REVIEWED_SOURCE_PATH)
    size, digest = codegen._REVIEWED_SOURCE_FINGERPRINT
    assert size == 13_198
    assert digest == "b90c9249e6c95f9738bac204d8ff973937549d0af602d0034bf95514a406f1a8"
    assert len(raw) == size
    assert hashlib.sha256(raw).hexdigest() == digest
    assert raw == codegen._canonical_document_bytes(
        codegen._parse_canonical_document(raw, label="reviewed source")
    )


def test_reviewed_source_closes_character_scene_all_roles_and_three_decisions() -> None:
    source = _value(codegen._REVIEWED_SOURCE_PATH)
    cases = codegen._assert_source_shape(source)
    assert tuple(case["case_id"] for case in cases) == codegen._CASE_IDS
    assert all(case["first_party_synthetic_subject"] is True for case in cases)
    reviews = [
        review
        for case in cases
        for review in cast(list[dict[str, object]], case["role_reviews"])
    ]
    assert [review["selected_reference_role"] for review in reviews] == [
        role for roles in codegen._ROLE_ORDER.values() for role in roles
    ]
    assert {review["expected_decision"] for review in reviews} == {
        "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
        "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
        "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"source_packet_scope": "REAL_SUBJECT"}), "identity"),
        (
            lambda value: value["cases"][0].update({"first_party_synthetic_subject": False}),
            "source anchor",
        ),
        (
            lambda value: value["cases"][0]["role_reviews"].reverse(),
            "selected role",
        ),
        (
            lambda value: value["cases"][0]["role_reviews"][0].update(
                {"expected_decision": "REJECT_ELIGIBLE_ASSET_ROLE_BINDING"}
            ),
            "expected decision",
        ),
        (
            lambda value: value["boundary_checks"]["fresh_replay"].update(
                {"expected_transition_count": 1}
            ),
            "replay",
        ),
    ],
)
def test_reviewed_source_mutations_fail_closed(
    mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    value = copy.deepcopy(_value(codegen._REVIEWED_SOURCE_PATH))
    mutation(value)
    with pytest.raises(codegen.GeneratedReferenceRoleBindingCodegenError, match=message):
        codegen._assert_source_shape(value)


def test_derived_packet_covers_the_frozen_role_binding_matrix() -> None:
    value = _value(codegen._DERIVED_FIXTURE_PATH)
    assert value["known_answer_version"] == "1.0.0"
    assert value["policy_document_sha256"] == codegen._POLICY_DOCUMENT_SHA256
    assert value["zero_authority_claim"] == (
        "TECHNICAL_KNOWN_ANSWER_ONLY_NO_RIGHTS_CURRENTNESS_PROVIDER_INPUT_OR_EXECUTION_AUTHORITY"
    )
    reviews = value["cases"]
    assert isinstance(reviews, list)
    assert len(reviews) == 7
    assert [item["selected_reference_role"] for item in reviews] == [
        role for roles in codegen._ROLE_ORDER.values() for role in roles
    ]
    assert {item["decision_disposition"] for item in reviews} == {
        "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING",
        "REJECT_ELIGIBLE_ASSET_ROLE_BINDING",
        "INDETERMINATE_ELIGIBLE_ASSET_ROLE_BINDING",
    }
    assert all(item["fresh_replay_transition_count"] == 2 for item in reviews)
    assert all(
        item["prohibited_media_operations"] == ["CROP", "SPLIT", "PROVIDER_INPUT"]
        for item in reviews
    )
    for item in reviews:
        assert item["binding_materialized"] is (
            item["decision_disposition"] == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
        )
        assert set(item["non_exclusive_boundary"].values()) == {False}
    checks = value["boundary_checks"]
    assert checks["equal_bytes_distinct_candidate_occurrence"] == {
        "expected_closure_identity_equal": False,
        "expected_media_bytes_equal": True,
        "expected_rule": (
            "CANDIDATE_OCCURRENCE_IDENTITY_REMAINS_DISTINCT_WHEN_RAW_PNG_BYTES_ARE_EQUAL"
        ),
    }
    assert checks["primary_binding_attack"]["expected_issue_code"] == (
        "PRIMARY_BINDING_NO_LONGER_ACTIVE"
    )
    assert checks["rights_scope_attacks"]["expected_error_code"] == "RIGHTS_SCOPE_MISMATCH"
    assert checks["prohibited_field_attacks"]["expected_error_code"] == (
        "PROHIBITED_BOUNDARY_CONNECTION"
    )
    assert checks["whole_media_boundary_attacks"]["mutations"] == [
        "CROP",
        "SPLIT",
        "PROVIDER_INPUT",
    ]


def test_derived_cases_are_exact_core_contract_documents_and_projections() -> None:
    value = _value(codegen._DERIVED_FIXTURE_PATH)
    cases = value["cases"]
    assert isinstance(cases, list)
    for item in cases:
        assert isinstance(item, dict)
        target_value = item["target"]
        request_value = item["request"]
        decision_value = item["decision"]
        assert isinstance(target_value, dict)
        assert isinstance(request_value, dict)
        assert isinstance(decision_value, dict)
        target = cast(
            role_binding.GeneratedReferenceEligibleAssetRoleBindingTargetV1,
            role_binding.GeneratedReferenceEligibleAssetRoleBindingTargetV1.model_validate_json(
                codegen._canonical_document_bytes(target_value)
            ),
        )
        request = cast(
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1,
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingRequestV1.model_validate_json(
                codegen._canonical_document_bytes(request_value)
            ),
        )
        decision = cast(
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1,
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingDecisionV1.model_validate_json(
                codegen._canonical_document_bytes(decision_value)
            ),
        )
        assert item["target_projection"] == (
            role_binding.generated_reference_role_binding_target_projection(target)
        )
        assert item["target_sha256"] == (
            role_binding.generated_reference_role_binding_target_sha256(target)
        )
        assert item["review_payload_projection"] == (
            role_binding.generated_reference_role_binding_review_payload_projection(request)
        )
        assert item["review_payload_sha256"] == (
            role_binding.generated_reference_role_binding_review_payload_sha256(request)
        )
        assert item["request_projection"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_request_projection(
                request
            )
        )
        assert item["request_sha256"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_request_sha256(
                request
            )
        )
        assert item["request_document_sha256"] == hashlib.sha256(
            role_binding.generated_reference_role_binding_contract_document_bytes(request)
        ).hexdigest()
        assert item["decision_projection"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_decision_projection(
                decision
            )
        )
        assert item["decision_sha256"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_decision_sha256(
                decision
            )
        )
        assert item["decision_document_sha256"] == hashlib.sha256(
            role_binding.generated_reference_role_binding_contract_document_bytes(decision)
        ).hexdigest()
        binding_value = item["binding"]
        if binding_value is None:
            assert item["binding_projection"] is None
            assert item["binding_sha256"] is None
            assert item["binding_document_sha256"] is None
            assert item["decision_disposition"] != "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"
            continue
        assert isinstance(binding_value, dict)
        binding = cast(
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1,
            role_binding.CreativeSampleGeneratedReferenceEligibleAssetRoleBindingV1.model_validate_json(
                codegen._canonical_document_bytes(binding_value)
            ),
        )
        assert item["binding_projection"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_projection(
                binding
            )
        )
        assert item["binding_sha256"] == (
            role_binding.creative_sample_generated_reference_eligible_asset_role_binding_sha256(
                binding
            )
        )
        assert item["binding_document_sha256"] == hashlib.sha256(
            role_binding.generated_reference_role_binding_contract_document_bytes(binding)
        ).hexdigest()
        assert item["decision_disposition"] == "APPROVE_ELIGIBLE_ASSET_ROLE_BINDING"


def test_derived_packet_binds_source_and_all_eighteen_upstream_inputs() -> None:
    value = _value(codegen._DERIVED_FIXTURE_PATH)
    source_raw = _raw(codegen._REVIEWED_SOURCE_PATH)
    assert value["reviewed_source"] == {
        "path": codegen._REVIEWED_SOURCE_PATH,
        "raw_sha256": hashlib.sha256(source_raw).hexdigest(),
        "size_bytes": len(source_raw),
    }
    upstream = value["upstream_inputs"]
    assert isinstance(upstream, list)
    assert [item["path"] for item in upstream] == list(
        codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS
    )
    assert [
        (item["size_bytes"], item["raw_sha256"])
        for item in upstream
    ] == list(codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS.values())


def test_complete_known_answer_closure_is_deterministic_and_checked_in(
    expected_closure: codegen._ExpectedClosure,
) -> None:
    closure = expected_closure
    actual = _raw(codegen._DERIVED_FIXTURE_PATH)
    assert actual == closure.derived_raw
    assert actual == codegen._canonical_document_bytes(closure.derived_value)
    assert 1 <= len(actual) <= codegen._MAX_DERIVED_BYTES


def test_fixed_paths_are_literal_distinct_and_not_discovered() -> None:
    codegen._assert_fixed_paths()
    assert tuple(codegen._PROTECTED_FINGERPRINTS) == (
        codegen._REVIEWED_SOURCE_PATH,
        *codegen._FROZEN_OLD_FIXTURE_FINGERPRINTS,
    )
    assert Path(codegen._REVIEWED_SOURCE_PATH).parent == Path(codegen._FIXTURE_DIRECTORY)
    assert Path(codegen._DERIVED_FIXTURE_PATH).parent == Path(codegen._FIXTURE_DIRECTORY)


def test_check_mode_has_no_reachable_write_path(
    monkeypatch: pytest.MonkeyPatch,
    expected_closure: codegen._ExpectedClosure,
) -> None:
    def reject_write(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("--check reached the only write function")

    monkeypatch.setattr(codegen, "_write_exact_derived", reject_write)
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(codegen, "_build_expected_closure", lambda _root: expected_closure)
    assert codegen.main(["--check"]) == 0


def test_update_dispatches_only_the_fixed_derived_closure(
    monkeypatch: pytest.MonkeyPatch,
    expected_closure: codegen._ExpectedClosure,
) -> None:
    closure = expected_closure
    calls: list[tuple[Path, codegen._ExpectedClosure]] = []
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(codegen, "_build_expected_closure", lambda _root: closure)
    monkeypatch.setattr(codegen, "_update_closure", lambda root, value: calls.append((root, value)))
    monkeypatch.setattr(
        codegen,
        "_check_closure",
        lambda *_args: (_ for _ in ()).throw(AssertionError("--update reached check dispatch")),
    )
    assert codegen.main(["--update"]) == 0
    assert calls == [(ROOT, closure)]


def test_writer_rejects_every_non_allowlisted_destination(tmp_path: Path) -> None:
    raw = codegen._canonical_document_bytes({"fixed": True})
    with pytest.raises(
        codegen.GeneratedReferenceRoleBindingCodegenError,
        match="outside the single fixed",
    ):
        codegen._write_exact_derived(tmp_path.resolve(), codegen._REVIEWED_SOURCE_PATH, raw)


def test_cli_requires_exactly_one_mode_and_has_no_root_or_output_override() -> None:
    parser = codegen._argument_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args(["--check", "--update"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--check", "--root", "."])
    with pytest.raises(SystemExit):
        parser.parse_args(["--update", "--output", "elsewhere.json"])
    assert parser.parse_args(["--check"]).check is True
    assert parser.parse_args(["--update"]).update is True


def test_codegen_has_no_network_subprocess_environment_or_temporary_output_capability() -> None:
    source = (ROOT / "src/sdc/generated_reference_role_binding_codegen.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots.isdisjoint(
        {"httpx", "requests", "socket", "subprocess", "tempfile", "urllib"}
    )
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "os.replace" not in source
    assert "Path.replace" not in source
    assert "Path.rename" not in source
