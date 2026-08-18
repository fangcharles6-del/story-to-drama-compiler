from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import sdc.real_asset_qualification_instruction_preparer_v23 as preparer
from sdc.compiler import stable_id
from sdc.real_asset_qualification_instruction_preparer_v23 import (
    TrustedLocalInstructionPreparationError,
    TrustedLocalInstructionQuarantineRequired,
    finalize_instruction,
    main,
    prepare_workspace,
    verify_instruction,
)
from sdc.real_asset_qualification_v2 import (
    QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetQualificationRequestV2,
)

REQUESTED_AT = "2030-01-01T00:00:00Z"
PREPARED_AT = "2030-01-01T01:00:00Z"
DECISION_AT = "2030-01-01T02:00:00Z"
OBSERVED_AT = "2030-01-01T03:00:00Z"
VALID_UNTIL = "2030-01-02T00:00:00Z"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def _id(prefix: str, label: str) -> str:
    return f"{prefix}_{_sha(label)[:20]}"


def _request() -> CreativeSampleRealAssetQualificationRequestV2:
    payload: dict[str, object] = {
        "schema_version": "2.0.0",
        "document_type": "sdc.creative-sample-real-asset-qualification-request-v2",
        "profile": "creative-sample-real-asset-qualification-assessment-v2",
        "policy_id": "creative-sample-real-asset-qualification-policy",
        "policy_version": "2.0.0",
        "policy_document_sha256": QUALIFICATION_V2_POLICY_DOCUMENT_SHA256,
        "requested_at": REQUESTED_AT,
        "evaluated_at": REQUESTED_AT,
        "request_valid_until": VALID_UNTIL,
        "evidence_valid_until": "PERPETUAL",
        "pack_id": _id("real_asset_pack", "pack"),
        "pack_manifest_sha256": _sha("manifest"),
        "rights_evidence_bundle_id": _id("real_asset_rights_evidence_v2", "evidence"),
        "rights_evidence_bundle_sha256": _sha("evidence-contract"),
        "evidence_retained_record_sha256": _sha("evidence-record"),
        "evidence_preparer_ref_sha256": _sha("evidence-preparer"),
        "review_a_id": _id("real_asset_pack_review_v2", "review-a"),
        "review_a_contract_sha256": _sha("review-a-contract"),
        "review_a_record_sha256": _sha("review-a-record"),
        "reviewer_a_retained_record_sha256": _sha("reviewer-a-retained"),
        "review_b_id": _id("real_asset_pack_review_v2", "review-b"),
        "review_b_contract_sha256": _sha("review-b-contract"),
        "review_b_record_sha256": _sha("review-b-record"),
        "reviewer_b_retained_record_sha256": _sha("reviewer-b-retained"),
        "pair_check_id": _id("real_asset_review_pair_check_v2", "pair"),
        "pair_check_sha256": _sha("pair-contract"),
        "status": "QUALIFICATION_REQUESTED",
        "rights_manifest_created": False,
        "rights_qualification_performed": False,
        "current_gate": "HUMAN_GATE",
        "provider_state": "NOT_AUTHORIZED",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
    }
    payload["request_id"] = stable_id("real_asset_qualification_request_v2", payload)
    return CreativeSampleRealAssetQualificationRequestV2.model_validate(payload, strict=True)


@dataclass(frozen=True)
class Prepared:
    request: Path
    qualifier: Path
    workspace: Path
    draft: Path
    output: Path


def _make_source_tree(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source-trust"
    source.mkdir(parents=True)
    request = source / "qualification-request-v2.json"
    request.write_bytes(_canonical(_request()))
    qualifier = source / "independent-qualifier-reference.txt"
    qualifier.write_text("synthetic independent qualifier reference\n", encoding="utf-8")
    return request, qualifier


def _prepare(tmp_path: Path) -> Prepared:
    request, qualifier = _make_source_tree(tmp_path)
    workspace_parent = tmp_path / "workspace-trust"
    workspace_parent.mkdir()
    workspace = workspace_parent / "qualification-instruction-workspace-v23"
    prepare_workspace(
        request,
        qualifier,
        workspace,
        observed_at=PREPARED_AT,
    )
    draft_parent = tmp_path / "draft-trust"
    draft_parent.mkdir()
    output_parent = tmp_path / "instruction-trust"
    output_parent.mkdir()
    return Prepared(
        request=request,
        qualifier=qualifier,
        workspace=workspace,
        draft=draft_parent / "qualification-instruction-draft-v23.json",
        output=output_parent / "qualification-instruction-v22.json",
    )


def _draft_payload(
    prepared: Prepared,
    *,
    decision: str = "PASS_ASSET_INTAKE_ONLY",
    issues: list[str] | None = None,
    basis: str = "Synthetic retained basis reviewed by an independent human qualifier.",
    decision_at: str = DECISION_AT,
) -> dict[str, object]:
    context_bytes = (prepared.workspace / "instruction-context.json").read_bytes()
    context = json.loads(context_bytes)
    if issues is None:
        issues = []
    return {
        "schema_version": "2.3.0",
        "document_type": (
            "sdc.creative-sample-real-asset-qualification-decision-instruction-draft-v2.3"
        ),
        "profile": "creative-sample-real-asset-qualification-instruction-preparation-v2.3",
        "status": "UNTRUSTED_DRAFT",
        "context_id": context["context_id"],
        "context_sha256": hashlib.sha256(context_bytes).hexdigest(),
        "request_id": context["request_id"],
        "request_sha256": context["request_sha256"],
        "qualifier_ref_sha256": context["qualifier_ref_sha256"],
        "decision_at": decision_at,
        "decision": decision,
        "qualification_issue_codes": issues,
        "qualification_basis": basis,
    }


def _write_draft(prepared: Prepared, **overrides: object) -> None:
    payload = _draft_payload(prepared)
    payload.update(overrides)
    prepared.draft.write_bytes(_canonical(payload))


@pytest.mark.parametrize(
    ("decision", "issues"),
    (
        ("PASS_ASSET_INTAKE_ONLY", []),
        ("REJECTED", ["QUALIFIER_REJECTED_ASSET_INTAKE"]),
        ("NEEDS_HUMAN_REVIEW", ["EVIDENCE_SCOPE_UNCLEAR"]),
    ),
)
def test_prepare_finalize_and_historical_verify_all_outcomes(
    tmp_path: Path,
    decision: str,
    issues: list[str],
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(
        prepared,
        decision=decision,
        qualification_issue_codes=issues,
    )

    instruction = finalize_instruction(
        prepared.request,
        prepared.qualifier,
        prepared.workspace,
        prepared.draft,
        prepared.output,
        observed_at=OBSERVED_AT,
    )

    assert instruction.decision == decision
    assert instruction.rights_qualification_performed is False
    assert instruction.rights_manifest_created is False
    assert instruction.execution_authorized is False
    assert instruction.posts_allowed == 0
    assert instruction.provider_requests == 0
    assert prepared.output.read_bytes() == _canonical(instruction)
    assert verify_instruction(
        prepared.request,
        prepared.qualifier,
        prepared.workspace,
        prepared.draft,
        prepared.output,
    ) == instruction


def test_workspace_is_exact_mechanical_five_file_closure(tmp_path: Path) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "instruction-workspace-v23"

    result = prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)

    assert {item.name for item in root.iterdir()} == {
        "app.js",
        "index.html",
        "instruction-context.js",
        "instruction-context.json",
        "style.css",
    }
    context = json.loads(result.context_path.read_bytes())
    assert len(context) == 26
    assert context["prepared_at"] == PREPARED_AT
    assert context["status"] == "AWAITING_EXPLICIT_QUALIFIER_INPUT"
    assert context["rights_qualification_performed"] is False
    assert context["execution_authorized"] is False
    script = (root / "instruction-context.js").read_text(encoding="utf-8")
    assert "Object.defineProperty" in script
    assert "sdcDeepFreeze" in script
    assert "writable: false" in script
    assert "configurable: false" in script


@pytest.mark.parametrize("mutation", ("missing", "extra", "asset", "context"))
def test_workspace_missing_extra_or_tampered_file_is_rejected(
    tmp_path: Path,
    mutation: str,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    if mutation == "missing":
        (prepared.workspace / "style.css").unlink()
    elif mutation == "extra":
        (prepared.workspace / "extra.txt").write_text("extra", encoding="utf-8")
    elif mutation == "asset":
        (prepared.workspace / "app.js").write_text("drift", encoding="utf-8")
    else:
        context_path = prepared.workspace / "instruction-context.json"
        context = json.loads(context_path.read_bytes())
        context["prepared_at"] = "2030-01-01T01:00:01Z"
        context_path.write_bytes(_canonical(context))
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


@pytest.mark.parametrize(
    "field",
    ("decision_at", "decision", "qualification_issue_codes", "qualification_basis"),
)
def test_each_human_field_is_required_and_never_inferred(
    tmp_path: Path,
    field: str,
) -> None:
    prepared = _prepare(tmp_path)
    payload = _draft_payload(prepared)
    del payload[field]
    prepared.draft.write_bytes(_canonical(payload))

    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )
    assert not prepared.output.exists()


@pytest.mark.parametrize(
    "field",
    ("context_id", "context_sha256", "request_id", "request_sha256", "qualifier_ref_sha256"),
)
def test_each_mechanical_draft_binding_is_checked_against_context(
    tmp_path: Path,
    field: str,
) -> None:
    prepared = _prepare(tmp_path)
    payload = _draft_payload(prepared)
    if field == "context_id":
        payload[field] = "real_asset_qualification_instruction_context_v23_" + "f" * 20
    elif field == "request_id":
        payload[field] = "real_asset_qualification_request_v2_" + "f" * 20
    else:
        payload[field] = "f" * 64
    prepared.draft.write_bytes(_canonical(payload))
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


@pytest.mark.parametrize("field", ("schema_version", "document_type", "profile", "status"))
def test_draft_fixed_fields_are_required(tmp_path: Path, field: str) -> None:
    prepared = _prepare(tmp_path)
    payload = _draft_payload(prepared)
    del payload[field]
    prepared.draft.write_bytes(_canonical(payload))
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


@pytest.mark.parametrize(
    ("decision", "issues"),
    (
        ("PASS_ASSET_INTAKE_ONLY", ["EVIDENCE_SCOPE_UNCLEAR"]),
        ("REJECTED", ["OTHER_BLOCKING_ISSUE"]),
        ("NEEDS_HUMAN_REVIEW", []),
        ("NEEDS_HUMAN_REVIEW", ["QUALIFIER_REJECTED_ASSET_INTAKE"]),
    ),
)
def test_outcome_issue_rules_fail_closed(
    tmp_path: Path,
    decision: str,
    issues: list[str],
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(
        prepared,
        decision=decision,
        qualification_issue_codes=issues,
    )
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


@pytest.mark.parametrize(
    "mutator",
    (
        "unknown",
        "noncanonical",
        "duplicate",
        "bom",
        "nonfinite",
        "nonutf8",
        "unpaired-surrogate",
    ),
)
def test_untrusted_draft_rejects_json_ambiguity(tmp_path: Path, mutator: str) -> None:
    prepared = _prepare(tmp_path)
    payload = _draft_payload(prepared)
    if mutator == "unknown":
        payload["unknown"] = True
        raw = _canonical(payload)
    elif mutator == "noncanonical":
        raw = json.dumps(payload, ensure_ascii=False).encode()
    elif mutator == "duplicate":
        canonical = _canonical(payload).decode()
        raw = canonical.replace(
            '  "decision": "PASS_ASSET_INTAKE_ONLY",',
            '  "decision": "PASS_ASSET_INTAKE_ONLY",\n'
            '  "decision": "PASS_ASSET_INTAKE_ONLY",',
        ).encode()
    elif mutator == "bom":
        raw = b"\xef\xbb\xbf" + _canonical(payload)
    elif mutator == "nonfinite":
        raw = _canonical(payload).replace(b'"decision_at"', b'"extra": NaN,\n  "decision_at"')
    elif mutator == "nonutf8":
        raw = b"\xff\xfe"
    else:
        payload["qualification_basis"] = "\ud800"
        raw = (
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        ).encode()
    prepared.draft.write_bytes(raw)

    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


@pytest.mark.parametrize(
    ("decision_at", "observed_at"),
    (
        (REQUESTED_AT, OBSERVED_AT),
        (DECISION_AT, PREPARED_AT),
        (VALID_UNTIL, "2030-01-02T00:00:01Z"),
        ("2030-01-01T02:00:00+00:00", OBSERVED_AT),
    ),
)
def test_finalize_enforces_explicit_monotonic_time_window(
    tmp_path: Path,
    decision_at: str,
    observed_at: str,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared, decision_at=decision_at)
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=observed_at,
        )


def test_prepare_and_finalize_accept_exact_inclusive_lower_time_boundaries(
    tmp_path: Path,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    workspace_parent = tmp_path / "workspace-trust"
    workspace_parent.mkdir()
    workspace = workspace_parent / "workspace-v23"
    prepare_workspace(request, qualifier, workspace, observed_at=REQUESTED_AT)
    draft_parent = tmp_path / "draft-trust"
    output_parent = tmp_path / "instruction-trust"
    draft_parent.mkdir()
    output_parent.mkdir()
    prepared = Prepared(
        request,
        qualifier,
        workspace,
        draft_parent / "qualification-instruction-draft-v23.json",
        output_parent / "qualification-instruction-v22.json",
    )
    _write_draft(prepared, decision_at=REQUESTED_AT)
    finalized = finalize_instruction(
        request,
        qualifier,
        workspace,
        prepared.draft,
        prepared.output,
        observed_at=REQUESTED_AT,
    )
    assert finalized.decision_at == REQUESTED_AT


@pytest.mark.parametrize(
    "basis",
    (" leading", "trailing ", "e\u0301", "control\u0007", "x" * 1001),
)
def test_basis_text_is_explicit_bounded_trimmed_nfc_and_control_free(
    tmp_path: Path,
    basis: str,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared, qualification_basis=basis)
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


def test_workspace_and_instruction_are_create_new_only(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    marker = prepared.workspace / "operator-marker.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            observed_at=PREPARED_AT,
        )
    assert marker.read_text(encoding="utf-8") == "preserve"
    prepared.output.write_text("preserve", encoding="utf-8")
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )
    assert prepared.output.read_text(encoding="utf-8") == "preserve"


def test_path_aliases_outcome_names_and_intersecting_trust_areas_are_rejected(
    tmp_path: Path,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(
            request,
            qualifier,
            request.parent / "workspace-v23",
            observed_at=PREPARED_AT,
        )


@pytest.mark.parametrize("location", ("source", "workspace", "draft", "containing", "nested"))
def test_instruction_output_parent_is_a_separate_trust_area(
    tmp_path: Path,
    location: str,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    if location == "source":
        output = prepared.request.parent / "instruction-v22.json"
    elif location == "workspace":
        output = prepared.workspace / "instruction-v22.json"
    elif location == "draft":
        output = prepared.draft.parent / "instruction-v22.json"
    elif location == "containing":
        output = tmp_path / "instruction-v22.json"
    else:
        nested = prepared.request.parent / "nested-output"
        nested.mkdir()
        output = nested / "instruction-v22.json"
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            output,
            observed_at=OBSERVED_AT,
        )


def test_mutable_alias_component_is_rejected_for_every_operation(tmp_path: Path) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    alias_parent = tmp_path / "latest-source"
    alias_parent.mkdir()
    aliased_request = alias_parent / "request.json"
    aliased_request.write_bytes(request.read_bytes())
    workspace_parent = tmp_path / "workspace-trust"
    workspace_parent.mkdir()
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(
            aliased_request,
            qualifier,
            workspace_parent / "workspace-v23",
            observed_at=PREPARED_AT,
        )

    prepared = _prepare(tmp_path / "separate")
    outcome_draft = prepared.draft.with_name("qualification-pass.json")
    outcome_draft.write_bytes(_canonical(_draft_payload(prepared)))
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            outcome_draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )


def test_symlink_and_hardlink_inputs_are_rejected(tmp_path: Path) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    linked = tmp_path / "linked-request.json"
    try:
        linked.symlink_to(request)
    except OSError:
        pytest.skip("host cannot create a local symlink")
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(linked, qualifier, parent / "workspace-v23", observed_at=PREPARED_AT)

    linked.unlink()
    hardlink = tmp_path / "hardlink-ref.txt"
    try:
        os.link(qualifier, hardlink)
    except OSError:
        pytest.skip("host cannot create a hard link")
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(request, qualifier, parent / "workspace-v24", observed_at=PREPARED_AT)


def test_workspace_postwrite_failure_rolls_back_exact_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"

    def fail_capture(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("synthetic postwrite fault")

    monkeypatch.setattr(preparer, "_capture_created_workspace", fail_capture)
    with pytest.raises(RuntimeError, match="postwrite"):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert not root.exists()


def test_workspace_final_exact_fd_commit_check_catches_last_window_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"
    original_commit = preparer._commit_workspace

    def mutate_then_commit(
        created: Any,
        expected_payloads: dict[str, bytes],
    ) -> None:
        descriptors = created.descriptors
        descriptor = descriptors["app.js"]
        os.lseek(descriptor, 0, os.SEEK_SET)
        assert os.write(descriptor, b"DRIFT") == 5
        original_commit(created, expected_payloads)

    monkeypatch.setattr(preparer, "_commit_workspace", mutate_then_commit)
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert not root.exists()


def test_workspace_final_member_set_check_catches_late_extra_without_deleting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"
    original_read = preparer._read_open_workspace_file
    context_script_reads = 0

    def read_and_add_extra(
        created: Any,
        name: str,
        expected: bytes,
    ) -> tuple[int, int]:
        nonlocal context_script_reads
        result = original_read(created, name, expected)
        if name == "instruction-context.js":
            context_script_reads += 1
            if context_script_reads == 3:
                (root / "operator-extra.txt").write_text(
                    "preserve",
                    encoding="utf-8",
                )
        return result

    monkeypatch.setattr(preparer, "_read_open_workspace_file", read_and_add_extra)
    with pytest.raises(TrustedLocalInstructionQuarantineRequired):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert (root / "operator-extra.txt").read_text(encoding="utf-8") == "preserve"


def test_workspace_first_root_seal_failure_requires_explicit_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"
    original = preparer._directory_identity

    def identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
        if path == root and root.exists():
            raise TrustedLocalInstructionPreparationError("synthetic first root seal fault")
        return original(path, field=field)

    monkeypatch.setattr(preparer, "_directory_identity", identity)
    with pytest.raises(TrustedLocalInstructionQuarantineRequired):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert root.exists()


@pytest.mark.parametrize("fault", ("short-write", "fsync", "interrupt"))
def test_workspace_midwrite_faults_remove_exact_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"
    if fault in {"short-write", "interrupt"}:
        original_write = os.write
        calls = 0

        def write(descriptor: int, data: bytes) -> int:
            nonlocal calls
            calls += 1
            if calls == 2:
                if fault == "interrupt":
                    raise KeyboardInterrupt
                return 0
            return int(original_write(descriptor, data))

        monkeypatch.setattr(os, "write", write)
        expected: type[BaseException] = (
            KeyboardInterrupt if fault == "interrupt" else TrustedLocalInstructionPreparationError
        )
    else:
        original_fsync = os.fsync
        calls = 0

        def fsync(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic fsync fault")
            original_fsync(descriptor)

        monkeypatch.setattr(os, "fsync", fsync)
        expected = TrustedLocalInstructionPreparationError
    with pytest.raises(expected):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert not root.exists()


def test_workspace_replacement_is_never_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.name == "nt":
        pytest.skip("Windows retained handles deny replacement before this branch")
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"

    def replace_then_fail(*args: object, **kwargs: object) -> object:
        del args, kwargs
        target = root / "index.html"
        target.unlink()
        target.write_text("replacement", encoding="utf-8")
        raise RuntimeError("replacement fault")

    monkeypatch.setattr(preparer, "_capture_created_workspace", replace_then_fail)
    with pytest.raises(TrustedLocalInstructionQuarantineRequired):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert (root / "index.html").read_text(encoding="utf-8") == "replacement"


def test_workspace_delete_and_primary_invalidation_failure_quarantines_poisoned_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"

    def fail_capture(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("synthetic postwrite rollback fault")

    monkeypatch.setattr(preparer, "_capture_created_workspace", fail_capture)
    monkeypatch.setattr(preparer, "_invalidate_open", lambda descriptor: False)
    if os.name == "nt":
        monkeypatch.setattr(preparer, "_delete_open_windows", lambda descriptor: False)
    else:
        monkeypatch.setattr(
            preparer,
            "_unlink_open_posix_workspace_file",
            lambda *args, **kwargs: False,
        )
    with pytest.raises(TrustedLocalInstructionQuarantineRequired):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)
    assert root.exists()
    context_residue = root / "instruction-context.json"
    assert context_residue.read_bytes().startswith(b"\0")
    with pytest.raises((UnicodeDecodeError, json.JSONDecodeError)):
        json.loads(context_residue.read_bytes().decode("utf-8"))


def test_windows_workspace_guard_close_failure_requires_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.name != "nt":
        pytest.skip("Windows CloseHandle contract")
    request, qualifier = _make_source_tree(tmp_path)
    parent = tmp_path / "workspace-trust"
    parent.mkdir()
    root = parent / "workspace-v23"

    def fail_capture(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError("synthetic rollback fault")

    monkeypatch.setattr(preparer, "_capture_created_workspace", fail_capture)
    monkeypatch.setattr(
        preparer,
        "_close_windows_handle",
        lambda handle: (_ for _ in ()).throw(OSError("CloseHandle failed")),
    )
    with pytest.raises(TrustedLocalInstructionQuarantineRequired):
        prepare_workspace(request, qualifier, root, observed_at=PREPARED_AT)


def test_instruction_postwrite_failure_removes_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    original = preparer._capture_finalize
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise SystemExit(9)
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer, "_capture_finalize", capture)
    with pytest.raises(SystemExit):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )
    assert not prepared.output.exists()


def test_verify_rejects_tampered_instruction_without_writing_any_input(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    instruction = finalize_instruction(
        prepared.request,
        prepared.qualifier,
        prepared.workspace,
        prepared.draft,
        prepared.output,
        observed_at=OBSERVED_AT,
    )
    payload = instruction.model_dump(mode="json")
    payload["qualification_basis"] = "Tampered but canonical basis."
    prepared.output.write_bytes(_canonical(payload))
    before = {
        path: path.read_bytes()
        for path in (prepared.request, prepared.qualifier, prepared.draft)
    }
    with pytest.raises(TrustedLocalInstructionPreparationError):
        verify_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
        )
    assert {path: path.read_bytes() for path in before} == before


def test_capture_drift_of_draft_fails_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(tmp_path)
    _write_draft(prepared)
    original = preparer._capture_finalize
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            payload = _draft_payload(prepared, basis="A different explicit human basis.")
            prepared.draft.write_bytes(_canonical(payload))
        return original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preparer, "_capture_finalize", capture)
    with pytest.raises(TrustedLocalInstructionPreparationError):
        finalize_instruction(
            prepared.request,
            prepared.qualifier,
            prepared.workspace,
            prepared.draft,
            prepared.output,
            observed_at=OBSERVED_AT,
        )
    assert not prepared.output.exists()


def test_request_embedded_reserved_digest_cannot_alias_qualifier_reference(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source-trust"
    source.mkdir()
    qualifier = source / "qualifier.txt"
    qualifier.write_text("synthetic qualifier alias target\n", encoding="utf-8")
    request = _request().model_dump(mode="json")
    request["evidence_retained_record_sha256"] = hashlib.sha256(
        qualifier.read_bytes()
    ).hexdigest()
    request.pop("request_id")
    request["request_id"] = stable_id("real_asset_qualification_request_v2", request)
    request_path = source / "request.json"
    request_path.write_bytes(_canonical(request))
    workspace_parent = tmp_path / "workspace-trust"
    workspace_parent.mkdir()
    with pytest.raises(TrustedLocalInstructionPreparationError):
        prepare_workspace(
            request_path,
            qualifier,
            workspace_parent / "workspace-v23",
            observed_at=PREPARED_AT,
        )


def test_quarantine_status_is_fixed_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "PRIVATE_ROLLBACK_PATH_SHA_BASIS"

    def quarantine(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise TrustedLocalInstructionQuarantineRequired(marker)

    monkeypatch.setattr(preparer, "finalize_instruction", quarantine)
    code = main(
        [
            "finalize-instruction",
            "--request",
            "C:/private/request.json",
            "--qualifier-ref",
            "C:/private/qualifier.txt",
            "--workspace",
            "C:/private/workspace",
            "--draft",
            "C:/private/draft.json",
            "--output",
            "C:/private/instruction.json",
            "--observed-at",
            OBSERVED_AT,
        ]
    )
    captured = capsys.readouterr()
    assert code == 3
    assert "ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED" in captured.err
    assert marker not in captured.err


def test_cli_is_redacted_and_has_exact_command_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    marker = "PRIVATE_PATH_SHA_BASIS_PASS"

    def fail(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise RuntimeError(marker)

    monkeypatch.setattr(preparer, "prepare_workspace", fail)
    result = main(
        [
            "prepare-workspace",
            "--request",
            str(tmp_path / marker / "request.json"),
            "--qualifier-ref",
            str(tmp_path / marker / "qualifier.txt"),
            "--workspace",
            str(tmp_path / marker / "workspace"),
            "--observed-at",
            PREPARED_AT,
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert marker not in captured.out + captured.err
    assert "FAILED_CLOSED" in captured.err
    assert "traceback" not in captured.err.casefold()

    source = Path(preparer.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    commands = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_parser"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert commands == {"prepare-workspace", "finalize-instruction", "verify-instruction"}


def test_cli_success_never_reports_id_hash_path_or_human_content(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    context_id = "real_asset_qualification_instruction_context_v23_" + "a" * 20
    marker = "PRIVATE_HUMAN_BASIS"
    result = preparer.TrustedLocalInstructionWorkspace(
        root=Path("C:/opaque"),
        index_path=Path("C:/opaque/index.html"),
        context_path=Path("C:/opaque/instruction-context.json"),
        context_id=context_id,
        context_sha256="b" * 64,
    )
    monkeypatch.setattr(preparer, "prepare_workspace", lambda *args, **kwargs: result)
    assert main(
        [
            "prepare-workspace",
            "--request",
            "C:/private/request.json",
            "--qualifier-ref",
            "C:/private/qualifier.txt",
            "--workspace",
            "C:/private/workspace",
            "--observed-at",
            PREPARED_AT,
        ]
    ) == 0
    output = capsys.readouterr().out
    assert "AWAITING_EXPLICIT_QUALIFIER_INPUT" in output
    for forbidden in (context_id, "b" * 64, "C:/private", marker, "artifact_id"):
        assert forbidden not in output


def test_help_remains_normal_but_operation_baseexceptions_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    capsys.readouterr()

    monkeypatch.setattr(
        preparer,
        "verify_instruction",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    result = main(
        [
            "verify-instruction",
            "--request",
            "C:/private/request.json",
            "--qualifier-ref",
            "C:/private/qualifier.txt",
            "--workspace",
            "C:/private/workspace",
            "--draft",
            "C:/private/draft.json",
            "--instruction",
            "C:/private/instruction.json",
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert "FAILED_CLOSED" in captured.err
    assert "Traceback" not in captured.err


def test_ast_has_no_forbidden_operational_dependency() -> None:
    source = Path(preparer.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_roots = {
        "http",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(banned_roots)
    forbidden_identifiers = {
        "build_real_asset_qualification_decision_v2",
        "verify_real_asset_qualification_closure_v2",
        "real_asset_qualification_decision_finalizer_v22",
        "rights_manifest",
    }
    used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert used_names.isdisjoint(forbidden_identifiers)
    assert "datetime.now" not in source
    assert "datetime.utcnow" not in source
    assert "os.environ" not in source
