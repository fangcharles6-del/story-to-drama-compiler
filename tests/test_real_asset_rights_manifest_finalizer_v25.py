from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from test_real_asset_qualification_decision_finalizer_v22 import (
    DECISION_AT,
    OBSERVED_AT,
    SyntheticDecisionClosure,
    _canonical_document,
)
from test_real_asset_qualification_decision_finalizer_v22 import (
    closure as _decision_closure_fixture,
)

import sdc.real_asset_rights_manifest_finalizer_v25 as finalizer_module
from sdc.real_asset_intake import (
    FrozenRealAssetPack,
)
from sdc.real_asset_media import (
    PngTechnicalEvidence,
    SafeLocalFile,
    WavTechnicalEvidence,
    read_safe_local_file,
)
from sdc.real_asset_qualification_decision_finalizer_v22 import finalize_decision
from sdc.real_asset_qualification_v2 import (
    CreativeSampleRealAssetQualificationDecisionV2,
)
from sdc.real_asset_rights_manifest_finalizer_v25 import (
    TrustedLocalRightsManifestFinalizationError,
    TrustedLocalRightsManifestPaths,
    TrustedLocalRightsManifestQuarantineRequired,
    finalize_manifest,
    inspect_manifest_ready,
    main,
    verify_manifest,
)
from sdc.real_asset_rights_manifest_v24 import (
    CreativeSampleRealAssetRightsManifestV2,
    RealAssetRightsManifestV24Error,
    parse_real_asset_rights_manifest_v2_json,
)

MANIFEST_AT = "2026-08-19T12:00:00Z"


@dataclass(frozen=True)
class SyntheticManifestClosure:
    paths: TrustedLocalRightsManifestPaths
    decision_closure: SyntheticDecisionClosure
    decision: CreativeSampleRealAssetQualificationDecisionV2
    decision_path: Path


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_file(path: Path) -> SafeLocalFile:
    return read_safe_local_file(path, max_bytes=64 * 1024 * 1024)


@pytest.fixture
def closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> SyntheticManifestClosure:
    factory = _decision_closure_fixture.__wrapped__
    decision_closure: SyntheticDecisionClosure = factory(tmp_path, monkeypatch)
    decision_parent = (tmp_path / "decision-area").resolve()
    decision_parent.mkdir()
    decision_path = decision_parent / "qualification-decision-v2.json"
    decision = finalize_decision(
        decision_closure.paths,
        decision_path,
        observed_at=OBSERVED_AT,
    )

    by_path = {
        path: descriptor
        for path, descriptor in zip(
            decision_closure.paths.request_inputs.media_paths,
            decision_closure.pack.objects,
            strict=True,
        )
    }

    def inspect_png(
        path: Path,
        *,
        forbidden_sha256: tuple[str, ...] = (),
    ) -> tuple[SafeLocalFile, PngTechnicalEvidence]:
        del forbidden_sha256
        descriptor = by_path[path]
        assert descriptor.image is not None
        return _safe_file(path), PngTechnicalEvidence(
            **descriptor.image.model_dump(mode="python")
        )

    def inspect_voice_wav(
        path: Path,
        *,
        maximum_duration_ms: int,
    ) -> tuple[SafeLocalFile, WavTechnicalEvidence]:
        del maximum_duration_ms
        descriptor = by_path[path]
        assert descriptor.audio is not None
        return _safe_file(path), WavTechnicalEvidence(
            **descriptor.audio.model_dump(mode="python")
        )

    def inspect_bgm_wav(path: Path) -> tuple[SafeLocalFile, WavTechnicalEvidence]:
        descriptor = by_path[path]
        assert descriptor.audio is not None
        return _safe_file(path), WavTechnicalEvidence(
            **descriptor.audio.model_dump(mode="python")
        )

    monkeypatch.setattr(finalizer_module, "inspect_png", inspect_png)
    monkeypatch.setattr(finalizer_module, "inspect_voice_wav", inspect_voice_wav)
    monkeypatch.setattr(finalizer_module, "inspect_bgm_wav", inspect_bgm_wav)
    return SyntheticManifestClosure(
        paths=TrustedLocalRightsManifestPaths(
            decision_inputs=decision_closure.paths,
            decision=decision_path.resolve(),
        ),
        decision_closure=decision_closure,
        decision=decision,
        decision_path=decision_path.resolve(),
    )


def _manifest_output(tmp_path: Path, name: str = "rights-manifest-v2.json") -> Path:
    parent = (tmp_path / "manifest-area").resolve()
    parent.mkdir(exist_ok=True)
    return parent / name


def _assert_ordinary_rollback_result(output: Path) -> None:
    if sys.platform == "win32":
        assert not output.exists()
        return

    assert stat.S_ISREG(output.lstat().st_mode)
    raw = output.read_bytes()
    assert raw == b"" or raw.startswith(b"\0")
    with pytest.raises(RealAssetRightsManifestV24Error):
        parse_real_asset_rights_manifest_v2_json(raw)


def _cli_args(paths: TrustedLocalRightsManifestPaths) -> list[str]:
    request = paths.decision_inputs.request_inputs
    values = [
        "--pack-root",
        str(request.pack_root),
        "--pack-manifest",
        str(request.pack_manifest),
    ]
    for path in request.media_paths:
        values.extend(("--media-path", str(path)))
    values.extend(
        (
            "--evidence",
            str(request.evidence_bundle),
            "--reviewer-a",
            str(request.reviewer_a),
            "--reviewer-b",
            str(request.reviewer_b),
            "--pair-check",
            str(request.pair_check),
            "--evidence-retained-record",
            str(request.evidence_retained_record),
            "--evidence-preparer-ref",
            str(request.evidence_preparer_ref),
            "--reviewer-a-retained-record",
            str(request.reviewer_a_retained_record),
            "--reviewer-b-retained-record",
            str(request.reviewer_b_retained_record),
            "--request",
            str(paths.decision_inputs.request),
            "--qualifier-ref",
            str(paths.decision_inputs.qualifier_ref),
            "--instruction",
            str(paths.decision_inputs.qualifier_decision_record),
            "--decision",
            str(paths.decision),
        )
    )
    return values


def _assert_zero_execution_authority(
    value: CreativeSampleRealAssetRightsManifestV2,
) -> None:
    assert value.status == "RIGHTS_MANIFEST_CREATED"
    assert value.rights_qualification_performed is True
    assert value.rights_manifest_created is True
    assert value.current_gate == "HUMAN_GATE"
    assert value.provider_state == "NOT_AUTHORIZED"
    assert value.eligible_for_real_generation is False
    assert value.execution_authorized is False
    assert value.posts_allowed == value.provider_requests == 0


def test_exact_twenty_eight_explicit_paths_are_required(
    closure: SyntheticManifestClosure,
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    source_paths = finalizer_module._all_source_paths(normalized)
    assert len(source_paths) == 27
    assert len((normalized.decision_inputs.request_inputs.pack_root, *source_paths)) == 28
    assert len(set(source_paths)) == 27


def test_inspect_reads_two_complete_snapshots_without_building_or_writing(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_capture = finalizer_module._capture_snapshot
    captures = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal captures
        captures += 1
        return original_capture(*args, **kwargs)

    def explode(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("inspect must not call the Manifest builder")

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", capture)
    monkeypatch.setattr(finalizer_module, "build_real_asset_rights_manifest_v2", explode)
    before = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    inspected = inspect_manifest_ready(closure.paths, manifest_at=MANIFEST_AT)
    after = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert captures == 2
    assert inspected == "READY_FOR_MANIFEST_FINALIZATION"
    assert not isinstance(inspected, BaseModel)
    assert closure.decision.decision_id not in inspected
    assert closure.decision.qualification_basis not in inspected
    assert before == after


def test_finalize_calls_builder_once_and_verify_rebuilds_historically(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path)
    original_builder = finalizer_module.build_real_asset_rights_manifest_v2
    calls = 0

    def build(*args: object, **kwargs: object) -> CreativeSampleRealAssetRightsManifestV2:
        nonlocal calls
        calls += 1
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "build_real_asset_rights_manifest_v2", build)
    finalized = finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert calls == 1
    assert output.read_bytes() == _canonical_document(finalized)
    assert parse_real_asset_rights_manifest_v2_json(output.read_bytes()) == finalized
    _assert_zero_execution_authority(finalized)

    def no_builder(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("verify must not call the Manifest builder")

    monkeypatch.setattr(finalizer_module, "build_real_asset_rights_manifest_v2", no_builder)
    verified = verify_manifest(closure.paths, output)
    assert verified == finalized


def test_finalize_and_verify_lock_the_complete_event_order(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "ordered-manifest.json")
    events: list[str] = []
    original_capture = finalizer_module._capture_snapshot
    original_builder = finalizer_module.build_real_asset_rights_manifest_v2
    original_create = finalizer_module._create_new_manifest
    original_commit = finalizer_module._commit_created_manifest

    def capture(*args: object, **kwargs: object) -> object:
        result = original_capture(*args, **kwargs)
        events.append(f"capture-{sum(item.startswith('capture-') for item in events) + 1}")
        return result

    def build(*args: object, **kwargs: object) -> CreativeSampleRealAssetRightsManifestV2:
        events.append("builder-1")
        return original_builder(*args, **kwargs)

    def create(*args: object, **kwargs: object) -> object:
        events.append("create-1")
        return original_create(*args, **kwargs)

    def commit(*args: object, **kwargs: object) -> None:
        events.append("commit-1")
        original_commit(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", capture)
    monkeypatch.setattr(finalizer_module, "build_real_asset_rights_manifest_v2", build)
    monkeypatch.setattr(finalizer_module, "_create_new_manifest", create)
    monkeypatch.setattr(finalizer_module, "_commit_created_manifest", commit)
    finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert events == [
        "capture-1",
        "capture-2",
        "builder-1",
        "create-1",
        "capture-3",
        "commit-1",
    ]

    events.clear()
    original_verify = finalizer_module.verify_real_asset_rights_manifest_closure_v2

    def verify_closure(*args: object, **kwargs: object) -> object:
        events.append("pure-verify-1")
        return original_verify(*args, **kwargs)

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("historical verify must neither build nor create")

    monkeypatch.setattr(
        finalizer_module,
        "verify_real_asset_rights_manifest_closure_v2",
        verify_closure,
    )
    monkeypatch.setattr(finalizer_module, "build_real_asset_rights_manifest_v2", forbidden)
    monkeypatch.setattr(finalizer_module, "_create_new_manifest", forbidden)
    verify_manifest(closure.paths, output)
    assert events == ["capture-1", "pure-verify-1", "capture-2"]


@pytest.mark.parametrize(
    "manifest_at",
    (
        "2026-08-18T10:39:59Z",
        "2026-08-20T00:00:00Z",
        "2026-08-20T00:00:01Z",
        "2026-08-19T12:00:00+00:00",
        "2026-08-19T12:00Z",
        "not-a-time",
    ),
)
def test_manifest_time_fails_closed_before_decision_at_expiry_or_noncanonical(
    closure: SyntheticManifestClosure,
    manifest_at: str,
) -> None:
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        inspect_manifest_ready(closure.paths, manifest_at=manifest_at)


def test_manifest_at_equal_to_decision_and_after_request_expiry_is_allowed(
    closure: SyntheticManifestClosure,
) -> None:
    assert (
        inspect_manifest_ready(closure.paths, manifest_at=DECISION_AT)
        == "READY_FOR_MANIFEST_FINALIZATION"
    )
    assert closure.decision.request_valid_until < MANIFEST_AT
    assert (
        inspect_manifest_ready(closure.paths, manifest_at=MANIFEST_AT)
        == "READY_FOR_MANIFEST_FINALIZATION"
    )


def test_create_new_rejects_existing_target_and_never_overwrites(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    output = _manifest_output(tmp_path)
    marker = b"do not overwrite"
    output.write_bytes(marker)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.read_bytes() == marker


def test_successful_manifest_is_private_on_posix(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    output = _manifest_output(tmp_path)
    finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_module_exports_only_expected_public_boundary() -> None:
    assert finalizer_module.__all__ == [
        "TrustedLocalRightsManifestFinalizationError",
        "TrustedLocalRightsManifestPaths",
        "TrustedLocalRightsManifestQuarantineRequired",
        "finalize_manifest",
        "inspect_manifest_ready",
        "main",
        "verify_manifest",
    ]


def test_ast_has_no_remote_runtime_clock_scanning_or_v1_manifest_dependency() -> None:
    source = inspect.getsource(finalizer_module)
    tree = ast.parse(source)
    forbidden_text = (
        ".glob(",
        ".rglob(",
        "os.walk(",
        "os.scandir(",
        "datetime.now(",
        "datetime.utcnow(",
        "requests.",
        "httpx.",
        "build_real_asset_rights_manifest_v1",
        "qualify_real_asset",
    )
    for token in forbidden_text:
        assert token not in source
    forbidden_import_fragments = {
        "runtime",
        "worker",
        "provider",
        "postgres",
        "temporal",
        "ark",
        "ledger",
        "migration",
        "entitlement",
        "authorization",
    }
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not {
        name
        for name in imports
        if any(fragment in name.casefold() for fragment in forbidden_import_fragments)
    }
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
    assert commands == {
        "inspect-manifest-ready",
        "finalize-manifest",
        "verify-manifest",
    }


def test_cli_success_summaries_are_redacted_for_all_three_commands(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = _manifest_output(tmp_path)
    commands = (
        ["inspect-manifest-ready", *_cli_args(closure.paths), "--manifest-at", MANIFEST_AT],
        [
            "finalize-manifest",
            *_cli_args(closure.paths),
            "--manifest-at",
            MANIFEST_AT,
            "--output",
            str(output),
        ],
        ["verify-manifest", *_cli_args(closure.paths), "--manifest-file", str(output)],
    )
    expected = (
        ("inspect-manifest-ready", False, "READY_FOR_MANIFEST_FINALIZATION"),
        ("finalize-manifest", True, "RIGHTS_MANIFEST_CREATED"),
        ("verify-manifest", True, "RIGHTS_MANIFEST_CREATED"),
    )
    for argv, (operation, created, status) in zip(commands, expected, strict=True):
        assert main(argv) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        payload = json.loads(captured.out)
        serialized = captured.out
        assert payload["operation"] == operation
        assert payload["status"] == status
        assert payload["rights_manifest_created"] is created
        assert payload["rights_qualification_performed"] is True
        assert payload["current_gate"] == "HUMAN_GATE"
        assert payload["provider_state"] == "NOT_AUTHORIZED"
        assert payload["execution_authorized"] is False
        assert payload["posts_allowed"] == payload["provider_requests"] == 0
        for private in (
            str(closure.paths.decision),
            closure.decision.request_id,
            closure.decision.decision_id,
            closure.decision.qualification_basis,
            closure.decision.qualifier_ref_sha256,
        ):
            assert private not in serialized


def test_cli_failures_and_quarantine_are_redacted(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "PRIVATE-MARKER-DO-NOT-DISCLOSE"
    assert main(["inspect-manifest-ready", "--unknown", secret]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert secret not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"

    def quarantine(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise TrustedLocalRightsManifestQuarantineRequired(secret)

    monkeypatch.setattr(finalizer_module, "finalize_manifest", quarantine)
    output = _manifest_output(tmp_path)
    argv = [
        "finalize-manifest",
        *_cli_args(closure.paths),
        "--manifest-at",
        MANIFEST_AT,
        "--output",
        str(output),
    ]
    assert main(argv) == 3
    captured = capsys.readouterr()
    assert captured.out == ""
    assert secret not in captured.err
    assert json.loads(captured.err)["status"] == (
        "ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"
    )


def test_instruction_digest_is_the_only_expected_file_digest_binding_alias(
    closure: SyntheticManifestClosure,
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    snapshot = finalizer_module._capture_snapshot(normalized, manifest_at=MANIFEST_AT)
    assert snapshot.pair_check.status == "READY_FOR_SEPARATE_QUALIFICATION_REVIEW"
    assert snapshot.pair_check.issue_codes == ()
    instruction_sha256 = _sha256(
        normalized.decision_inputs.qualifier_decision_record.read_bytes()
    )
    assert instruction_sha256 == snapshot.decision.qualifier_record_sha256
    assert sum(item.sha256 == instruction_sha256 for item in snapshot.files) == 1


def test_policy_rejects_model_copy_bypass_of_every_zero_authority_constant(
    closure: SyntheticManifestClosure,
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    snapshot = finalizer_module._capture_snapshot(normalized, manifest_at=MANIFEST_AT)
    mutations: tuple[tuple[str, object], ...] = (
        ("decision", "REJECTED"),
        ("decision", "NEEDS_HUMAN_REVIEW"),
        ("qualification_scope", "RUNTIME_AND_ASSET_INTAKE"),
        ("status", "QUALIFICATION_PENDING"),
        ("rights_qualification_performed", False),
        ("eligible_for_separate_manifest_design_review", False),
        ("rights_manifest_created", True),
        ("current_gate", "RUNTIME_GATE"),
        ("provider_state", "AUTHORIZED"),
        ("eligible_for_real_generation", True),
        ("execution_authorized", True),
        ("posts_allowed", 1),
        ("provider_requests", 1),
    )
    for field, value in mutations:
        forged = replace(
            snapshot,
            decision=snapshot.decision.model_copy(update={field: value}),
        )
        with pytest.raises(TrustedLocalRightsManifestFinalizationError):
            finalizer_module._assert_manifest_policy_ready(
                forged,
                manifest_at=MANIFEST_AT,
            )


def test_policy_rejects_pack_media_provenance_or_technical_digest_aliases(
    closure: SyntheticManifestClosure,
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    snapshot = finalizer_module._capture_snapshot(normalized, manifest_at=MANIFEST_AT)
    original = snapshot.pack.manifest
    for field in ("sha256", "provenance_record_sha256", "technical_record_sha256"):
        objects = list(original.objects)
        objects[1] = objects[1].model_copy(
            update={field: getattr(objects[0], field)}
        )
        forged_manifest = original.model_copy(update={"objects": tuple(objects)})
        forged_pack = FrozenRealAssetPack(
            root=snapshot.pack.root,
            manifest_path=snapshot.pack.manifest_path,
            manifest=forged_manifest,
            created=False,
        )
        with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="distinct"):
            finalizer_module._assert_manifest_policy_ready(
                replace(snapshot, pack=forged_pack),
                manifest_at=MANIFEST_AT,
            )


def test_perpetual_evidence_has_no_synthetic_expiry_cutoff(
    closure: SyntheticManifestClosure,
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    snapshot = finalizer_module._capture_snapshot(normalized, manifest_at=MANIFEST_AT)
    perpetual = snapshot.evidence.model_copy(update={"valid_until": "PERPETUAL"})
    finalizer_module._assert_manifest_policy_ready(
        replace(snapshot, evidence=perpetual),
        manifest_at="9999-12-31T23:59:59Z",
    )


def test_path_count_order_absolute_and_duplicate_rules_fail_closed(
    closure: SyntheticManifestClosure,
) -> None:
    request = closure.paths.decision_inputs.request_inputs
    short_request = replace(request, media_paths=request.media_paths[:13])
    short_paths = replace(
        closure.paths,
        decision_inputs=replace(
            closure.paths.decision_inputs,
            request_inputs=short_request,
        ),
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="fourteen"):
        finalizer_module._normalize_paths(short_paths)

    swapped = list(request.media_paths)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    swapped_paths = replace(
        closure.paths,
        decision_inputs=replace(
            closure.paths.decision_inputs,
            request_inputs=replace(request, media_paths=tuple(swapped)),
        ),
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="manifest order"):
        inspect_manifest_ready(swapped_paths, manifest_at=MANIFEST_AT)

    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="absolute"):
        finalizer_module._normalize_paths(
            replace(closure.paths, decision=Path("decision.json"))
        )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="distinct"):
        finalizer_module._normalize_paths(
            replace(
                closure.paths,
                decision=closure.paths.decision_inputs.qualifier_decision_record,
            )
        )


def test_every_path_class_is_individually_required_to_be_absolute(
    closure: SyntheticManifestClosure,
) -> None:
    decision_inputs = closure.paths.decision_inputs
    request = decision_inputs.request_inputs

    request_cases = (
        replace(request, pack_root=Path("pack")),
        replace(request, pack_manifest=Path("asset-pack.json")),
        replace(
            request,
            media_paths=(Path("media.bin"), *request.media_paths[1:]),
        ),
        replace(request, evidence_bundle=Path("evidence.json")),
        replace(request, reviewer_a=Path("reviewer-a.json")),
        replace(request, reviewer_b=Path("reviewer-b.json")),
        replace(request, pair_check=Path("pair-check.json")),
        replace(request, evidence_retained_record=Path("evidence-record.txt")),
        replace(request, evidence_preparer_ref=Path("preparer-ref.txt")),
        replace(request, reviewer_a_retained_record=Path("reviewer-a-record.txt")),
        replace(request, reviewer_b_retained_record=Path("reviewer-b-record.txt")),
    )
    cases = [
        replace(
            closure.paths,
            decision_inputs=replace(decision_inputs, request_inputs=case),
        )
        for case in request_cases
    ]
    cases.extend(
        (
            replace(
                closure.paths,
                decision_inputs=replace(decision_inputs, request=Path("request.json")),
            ),
            replace(
                closure.paths,
                decision_inputs=replace(
                    decision_inputs,
                    qualifier_ref=Path("qualifier-ref.txt"),
                ),
            ),
            replace(
                closure.paths,
                decision_inputs=replace(
                    decision_inputs,
                    qualifier_decision_record=Path("instruction.json"),
                ),
            ),
            replace(closure.paths, decision=Path("decision.json")),
        )
    )
    for paths in cases:
        with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="absolute"):
            finalizer_module._normalize_paths(paths)


def test_pack_external_and_manifest_output_trust_areas_cannot_intersect(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    request = closure.paths.decision_inputs.request_inputs
    inside_pack = request.pack_root / "copied-evidence.json"
    inside_pack.write_bytes(request.evidence_bundle.read_bytes())
    intersecting = replace(
        closure.paths,
        decision_inputs=replace(
            closure.paths.decision_inputs,
            request_inputs=replace(request, evidence_bundle=inside_pack),
        ),
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="outside"):
        finalizer_module._normalize_paths(intersecting)

    nested_output_parent = closure.paths.decision.parent / "nested-output"
    nested_output_parent.mkdir()
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="trust area"):
        finalizer_module._validate_output(
            nested_output_parent / "manifest.json",
            paths=closure.paths,
        )

    missing_parent = (tmp_path / "missing-output-parent" / "manifest.json").resolve()
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalizer_module._validate_output(missing_parent, paths=closure.paths)


@pytest.mark.parametrize(
    "field",
    ("request", "qualifier_ref", "qualifier_decision_record", "decision"),
)
def test_all_post_request_private_paths_reject_mutable_aliases(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    field: str,
) -> None:
    decision_inputs = closure.paths.decision_inputs
    if field == "decision":
        original = closure.paths.decision
    else:
        original = getattr(decision_inputs, field)
    copied = (tmp_path / f"mutable-{field}" / f"latest-{original.name}").resolve()
    copied.parent.mkdir()
    copied.write_bytes(original.read_bytes())
    if field == "decision":
        paths = replace(closure.paths, decision=copied)
    else:
        paths = replace(
            closure.paths,
            decision_inputs=replace(decision_inputs, **{field: copied}),
        )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="mutable alias"):
        finalizer_module._normalize_paths(paths)


def test_repo_paths_unc_device_paths_and_outcome_output_names_are_rejected(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="Git tree"):
        finalizer_module._safe_absolute(
            Path(finalizer_module.__file__).resolve(),
            must_exist=True,
            field="synthetic source",
        )
    for raw in (r"\\server\share\record.json", r"\\.\C:\record.json"):
        with pytest.raises(TrustedLocalRightsManifestFinalizationError):
            finalizer_module._safe_absolute(
                Path(raw),
                must_exist=False,
                field="synthetic device path",
            )
    parent = (tmp_path / "outcome-area").resolve()
    parent.mkdir()
    for name in ("pass.json", "rejected.json", "needs-human-review.json"):
        with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="outcome"):
            finalizer_module._validate_output(parent / name, paths=closure.paths)


def test_symlink_hardlink_and_byte_digest_aliases_fail_closed_when_supported(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    original = closure.paths.decision_inputs.qualifier_ref
    linked = (tmp_path / "alias-area" / "qualifier-ref.txt").resolve()
    linked.parent.mkdir()
    try:
        os.link(original, linked)
    except OSError:
        linked = None
    if linked is not None:
        with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="non-linked"):
            finalizer_module._read_safe(linked, max_bytes=1024, field="hardlink")

    symbolic = (tmp_path / "alias-area" / "symbolic-ref.txt").resolve()
    try:
        symbolic.symlink_to(original)
    except OSError:
        symbolic = None
    if symbolic is not None:
        with pytest.raises(TrustedLocalRightsManifestFinalizationError):
            finalizer_module._read_safe(symbolic, max_bytes=1024, field="symlink")

    first = finalizer_module._FileSeal(Path("first"), "1" * 64, 1, (1, 1, 1, 1))
    digest_alias = finalizer_module._FileSeal(
        Path("second"),
        first.sha256,
        2,
        (1, 2, 2, 2),
    )
    physical_alias = finalizer_module._FileSeal(
        Path("third"),
        "2" * 64,
        3,
        first.identity,
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="digest alias"):
        finalizer_module._assert_non_aliasing((first, digest_alias))
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="physical"):
        finalizer_module._assert_non_aliasing((first, physical_alias))


def test_casefold_path_aliases_and_overlaps_fail_closed(
    closure: SyntheticManifestClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = finalizer_module._FileSeal(
        Path("C:/Synthetic/Record.json"),
        "1" * 64,
        1,
        (1, 1, 1, 1),
    )
    case_alias = finalizer_module._FileSeal(
        Path("c:/synthetic/record.JSON"),
        "2" * 64,
        2,
        (1, 2, 2, 2),
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="path alias"):
        finalizer_module._assert_non_aliasing((first, case_alias))
    assert finalizer_module._paths_overlap(first.path, case_alias.path)
    assert finalizer_module._paths_overlap(
        Path("C:/Synthetic/Area/Nested"),
        Path("c:/synthetic/area"),
    )
    assert finalizer_module._paths_overlap(
        Path("C:/Synthetic/Frozen-Pack/Contracts/Evidence.json"),
        Path("c:/synthetic/frozen-pack"),
    )

    source = closure.paths.decision
    target = Path(str(source).swapcase())
    monkeypatch.setattr(
        finalizer_module,
        "_safe_absolute",
        lambda path, must_exist, field: path,
    )
    monkeypatch.setattr(finalizer_module.os.path, "lexists", lambda path: False)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="overlaps"):
        finalizer_module._validate_output(target, paths=closure.paths)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="overlaps"):
        finalizer_module._validate_existing_manifest(target, paths=closure.paths)


@pytest.mark.parametrize("field", ("Request parent", "Decision parent"))
def test_request_and_decision_parent_physical_aliases_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    parent = Path("C:/synthetic/new-trust-parent")
    forbidden = Path("C:/synthetic/forbidden-trust-parent")

    def identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
        del field
        if path in {parent, forbidden}:
            return (11, 22, 0, 0)
        return (11, hash(path), 0, 0)

    monkeypatch.setattr(finalizer_module, "_directory_identity", identity)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="physically"):
        finalizer_module._assert_separate_trust_parent(
            parent,
            (forbidden,),
            field=field,
        )


def test_non_anchor_mount_component_is_rejected_but_anchor_is_not_inspected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mounted = tmp_path.parent
    calls: list[Path] = []

    def fake_mount(path: Path) -> bool:
        calls.append(path)
        return path == mounted

    monkeypatch.setattr(finalizer_module, "_is_mount_component", fake_mount)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="mounted"):
        finalizer_module._reject_non_anchor_mount_components(
            tmp_path,
            field="synthetic path",
        )
    assert Path(tmp_path.anchor) not in calls

    calls.clear()
    finalizer_module._reject_non_anchor_mount_components(
        Path(tmp_path.anchor),
        field="filesystem anchor",
    )
    assert calls == []

    monkeypatch.setattr(finalizer_module, "_is_mount_component", lambda path: False)
    monkeypatch.setattr(
        finalizer_module,
        "_linux_mount_points",
        lambda: frozenset({os.path.normpath(str(mounted))}),
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="mounted"):
        finalizer_module._reject_non_anchor_mount_components(
            tmp_path,
            field="synthetic bind path",
        )
    monkeypatch.setattr(
        finalizer_module,
        "_linux_mount_points",
        lambda: frozenset({os.path.normpath(tmp_path.anchor)}),
    )
    finalizer_module._reject_non_anchor_mount_components(
        Path(tmp_path.anchor),
        field="filesystem anchor",
    )


def test_linux_mountinfo_parses_bind_points_and_octal_escapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = (
        b"36 29 0:32 / /synthetic\\040bind rw,relatime - tmpfs tmpfs rw\n"
        b"37 29 0:33 / /synthetic/nested rw,relatime shared:1 - tmpfs tmpfs rw\n"
    )
    chunks = iter((raw, b""))
    monkeypatch.setattr(finalizer_module.sys, "platform", "linux")
    monkeypatch.setattr(finalizer_module.os, "open", lambda *args, **kwargs: 77)
    monkeypatch.setattr(
        finalizer_module.os,
        "read",
        lambda descriptor, maximum: next(chunks),
    )
    closed: list[int] = []
    monkeypatch.setattr(finalizer_module.os, "close", closed.append)
    assert finalizer_module._linux_mount_points() == frozenset(
        {
            os.path.normpath("/synthetic bind"),
            os.path.normpath("/synthetic/nested"),
        }
    )
    assert closed == [77]


@pytest.mark.parametrize("failure", ("read", "close", "oversize", "malformed", "utf8"))
def test_linux_mountinfo_failure_modes_are_bounded_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    monkeypatch.setattr(finalizer_module.sys, "platform", "linux")
    monkeypatch.setattr(finalizer_module.os, "open", lambda *args, **kwargs: 78)
    valid = b"36 29 0:32 / /synthetic rw - tmpfs tmpfs rw\n"
    if failure == "read":

        def reject_read(descriptor: int, maximum: int) -> bytes:
            del descriptor, maximum
            raise OSError("synthetic mountinfo read failure")

        monkeypatch.setattr(finalizer_module.os, "read", reject_read)
    else:
        if failure == "oversize":
            raw = b"x" * (finalizer_module._MOUNTINFO_MAX_BYTES + 1)
        elif failure == "malformed":
            raw = b"malformed mountinfo\n"
        elif failure == "utf8":
            raw = b"\xff"
        else:
            raw = valid
        chunks = iter((raw, b""))
        monkeypatch.setattr(
            finalizer_module.os,
            "read",
            lambda descriptor, maximum: next(chunks),
        )
    if failure == "close":

        def reject_close(descriptor: int) -> None:
            del descriptor
            raise OSError("synthetic mountinfo close failure")

        monkeypatch.setattr(finalizer_module.os, "close", reject_close)
    else:
        monkeypatch.setattr(finalizer_module.os, "close", lambda descriptor: None)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalizer_module._linux_mount_points()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows ADS contract")
def test_windows_alternate_data_stream_path_is_rejected(
    closure: SyntheticManifestClosure,
) -> None:
    original = closure.paths.decision_inputs.qualifier_ref
    ads = Path(f"{original}:synthetic-stream")
    try:
        ads.write_bytes(b"synthetic alternate stream")
    except OSError:
        pytest.skip("alternate data streams are unavailable")
    try:
        with pytest.raises(TrustedLocalRightsManifestFinalizationError):
            finalizer_module._safe_absolute(
                ads,
                must_exist=True,
                field="alternate stream",
            )
    finally:
        ads.unlink(missing_ok=True)


def test_mocked_reparse_directory_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ReparseDirectory:
        def lstat(self) -> object:
            return SimpleNamespace(
                st_dev=1,
                st_ino=2,
                st_size=0,
                st_mtime_ns=3,
                st_mode=stat.S_IFDIR,
                st_file_attributes=0x400,
            )

        def is_junction(self) -> bool:
            return True

    monkeypatch.setattr(
        finalizer_module,
        "_reject_non_anchor_mount_components",
        lambda path, field: None,
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="non-linked"):
        finalizer_module._directory_identity(
            ReparseDirectory(),  # type: ignore[arg-type]
            field=str(tmp_path),
        )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CloseHandle contract")
def test_windows_close_handle_false_is_an_error_and_parent_guard_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FalseCloseHandle:
        argtypes: object = None
        restype: object = None

        def __call__(self, handle: int) -> int:
            del handle
            return 0

    close_handle = FalseCloseHandle()

    class Kernel32:
        CloseHandle = close_handle

    monkeypatch.setattr(
        finalizer_module._windows_ctypes,
        "WinDLL",
        lambda *args, **kwargs: Kernel32(),
    )
    monkeypatch.setattr(finalizer_module._windows_ctypes, "get_last_error", lambda: 6)
    with pytest.raises(OSError, match="CloseHandle failed"):
        finalizer_module._close_windows_handle(101)
    target = finalizer_module._OutputTarget(
        path=(tmp_path / "unused.json").resolve(),
        parent=tmp_path.resolve(),
        parent_physical_identity=(1, 2),
    )
    created = finalizer_module._CreatedManifest(
        target=target,
        descriptor=102,
        parent_guard=103,
        windows_parent_guard=True,
    )
    with pytest.raises(OSError, match="CloseHandle failed"):
        finalizer_module._close_parent_guard(created)


@pytest.mark.skipif(os.name == "nt", reason="POSIX parent guard contract")
def test_posix_parent_guard_closes_fd_when_fstat_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = finalizer_module._OutputTarget(
        path=(tmp_path / "manifest.json").resolve(),
        parent=tmp_path.resolve(),
        parent_physical_identity=(1, 2),
    )
    sentinel = 9876
    closed: list[int] = []
    monkeypatch.setattr(finalizer_module.os, "open", lambda *args, **kwargs: sentinel)

    def reject_fstat(descriptor: int) -> object:
        assert descriptor == sentinel
        raise OSError("synthetic parent fstat failure")

    monkeypatch.setattr(finalizer_module.os, "fstat", reject_fstat)
    monkeypatch.setattr(finalizer_module.os, "close", closed.append)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="guarded"):
        finalizer_module._acquire_parent_guard(target)
    assert closed == [sentinel]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows raw HANDLE contract")
@pytest.mark.parametrize(
    ("delete_marked", "close_succeeds", "target_remains", "quarantine"),
    (
        (True, True, False, False),
        (False, True, False, True),
        (True, False, False, True),
        (True, True, True, True),
    ),
)
def test_windows_open_osfhandle_failure_requires_delete_close_and_absence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    delete_marked: bool,
    close_succeeds: bool,
    target_remains: bool,
    quarantine: bool,
) -> None:
    target = finalizer_module._OutputTarget(
        path=(tmp_path / "raw-handle-manifest.json").resolve(),
        parent=tmp_path.resolve(),
        parent_physical_identity=(1, 2),
    )
    if target_remains:
        target.path.write_bytes(b"independent target")

    class FakeCreateFile:
        argtypes: object = None
        restype: object = None

        def __call__(self, *args: object, **kwargs: object) -> int:
            del args, kwargs
            return 4242

    class Kernel32:
        CreateFileW = FakeCreateFile()

    monkeypatch.setattr(
        finalizer_module._windows_ctypes,
        "WinDLL",
        lambda name, use_last_error: Kernel32(),
    )

    def reject_conversion(*args: object, **kwargs: object) -> int:
        del args, kwargs
        raise OSError("synthetic open_osfhandle failure")

    monkeypatch.setattr(
        finalizer_module._windows_msvcrt,
        "open_osfhandle",
        reject_conversion,
    )
    monkeypatch.setattr(
        finalizer_module,
        "_mark_windows_handle_delete",
        lambda handle: delete_marked,
    )

    def close_raw_handle(handle: int) -> None:
        del handle
        if not close_succeeds:
            raise OSError("synthetic raw handle close failure")

    monkeypatch.setattr(finalizer_module, "_close_windows_handle", close_raw_handle)
    expected = (
        TrustedLocalRightsManifestQuarantineRequired if quarantine else OSError
    )
    with pytest.raises(expected):
        finalizer_module._open_windows_exclusive_manifest(target)
    if target_remains:
        assert target.path.read_bytes() == b"independent target"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CreateFileW contract")
def test_windows_createfile_uses_last_error_and_maps_exact_exists_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = finalizer_module._OutputTarget(
        path=(tmp_path / "exclusive-race.json").resolve(),
        parent=tmp_path.resolve(),
        parent_physical_identity=(1, 2),
    )
    calls: list[tuple[str, bool]] = []

    class ExistsCreateFile:
        argtypes: object = None
        restype: object = None

        def __call__(self, *args: object, **kwargs: object) -> int:
            del args, kwargs
            return finalizer_module._windows_ctypes.c_void_p(-1).value

    class Kernel32:
        CreateFileW = ExistsCreateFile()

    def windll(name: str, *, use_last_error: bool) -> object:
        calls.append((name, use_last_error))
        return Kernel32()

    monkeypatch.setattr(finalizer_module._windows_ctypes, "WinDLL", windll)
    monkeypatch.setattr(finalizer_module._windows_ctypes, "get_last_error", lambda: 183)
    with pytest.raises(FileExistsError):
        finalizer_module._open_windows_exclusive_manifest(target)
    assert calls == [("kernel32", True)]


@pytest.mark.parametrize(
    "raw_factory",
    (
        lambda canonical: b'{' + b'"status":"QUALIFICATION_COMPLETE",' + canonical[1:],
        lambda canonical: b"\xef\xbb\xbf" + canonical,
        lambda canonical: b"\xff\xfe" + canonical,
        lambda canonical: canonical.replace(b'"posts_allowed": 0', b'"posts_allowed": NaN'),
        lambda canonical: canonical.replace(
            b'"execution_authorized": false', b'"execution_authorized": 0'
        ),
        lambda canonical: canonical.replace(b'"posts_allowed": 0', b'"posts_allowed": false'),
        lambda canonical: b"{" + b" " * 1_048_576 + b"}",
        lambda canonical: json.dumps(json.loads(canonical), ensure_ascii=False).encode() + b"\n",
    ),
)
def test_decision_parser_rejects_duplicate_bom_nonfinite_oversize_and_noncanonical(
    closure: SyntheticManifestClosure,
    raw_factory: Callable[[bytes], bytes],
) -> None:
    canonical = _canonical_document(closure.decision)
    path = closure.paths.decision
    raw = raw_factory(canonical)
    path.write_bytes(raw)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalizer_module._read_decision(path)


def test_pair_request_instruction_decision_and_retained_binding_drift_fail_closed(
    closure: SyntheticManifestClosure,
) -> None:
    request_inputs = closure.paths.decision_inputs.request_inputs
    paths = (
        request_inputs.pair_check,
        closure.paths.decision_inputs.request,
        closure.paths.decision_inputs.qualifier_decision_record,
        closure.paths.decision,
        request_inputs.evidence_retained_record,
        request_inputs.evidence_preparer_ref,
        request_inputs.reviewer_a_retained_record,
        request_inputs.reviewer_b_retained_record,
        closure.paths.decision_inputs.qualifier_ref,
    )
    for path in paths:
        original = path.read_bytes()
        replacement = path.with_suffix(path.suffix + ".replacement")
        replacement.write_bytes(original + b"synthetic-drift")
        os.replace(replacement, path)
        try:
            with pytest.raises(TrustedLocalRightsManifestFinalizationError):
                inspect_manifest_ready(closure.paths, manifest_at=MANIFEST_AT)
        finally:
            path.write_bytes(original)


@pytest.mark.parametrize(
    ("status", "issues"),
    (
        ("NOT_READY", ()),
        ("READY_FOR_SEPARATE_QUALIFICATION_REVIEW", ("REVIEWS_DISAGREE",)),
    ),
)
def test_pair_check_must_be_exact_ready_status_with_empty_issues_even_after_model_copy(
    closure: SyntheticManifestClosure,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    issues: tuple[str, ...],
) -> None:
    normalized = finalizer_module._normalize_paths(closure.paths)
    original_read = finalizer_module._read_contract

    def read_contract(*args: object, **kwargs: object) -> tuple[object, object]:
        value, seal = original_read(*args, **kwargs)
        if kwargs.get("field") == "PairCheck contract":
            value = value.model_copy(  # type: ignore[attr-defined]
                update={"status": status, "issue_codes": issues}
            )
        return value, seal

    monkeypatch.setattr(finalizer_module, "_read_contract", read_contract)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="issue-free"):
        finalizer_module._capture_snapshot(normalized, manifest_at=MANIFEST_AT)


@pytest.mark.parametrize("mutate_after_capture", (1, 2))
def test_prewrite_and_postwrite_input_toctou_rolls_back(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate_after_capture: int,
) -> None:
    original_capture = finalizer_module._capture_snapshot
    instruction_path = closure.paths.decision_inputs.qualifier_decision_record
    raw = instruction_path.read_bytes()
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)
        calls += 1
        if calls == mutate_after_capture:
            replacement_path = instruction_path.with_suffix(".identity-replacement")
            replacement_path.write_bytes(raw)
            os.replace(replacement_path, instruction_path)
        return result

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", capture)
    output = _manifest_output(tmp_path, f"manifest-drift-{mutate_after_capture}.json")
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="drifted"):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    if mutate_after_capture == 1:
        assert not output.exists()
    else:
        _assert_ordinary_rollback_result(output)


def test_output_parent_identity_swap_is_rejected_before_create(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "parent-swap.json")
    parent = output.parent
    moved = parent.with_name("manifest-area-original")
    original_capture = finalizer_module._capture_snapshot
    calls = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        result = original_capture(*args, **kwargs)
        calls += 1
        if calls == 2:
            parent.rename(moved)
            parent.mkdir()
        return result

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", capture)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="parent identity"):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert not output.exists()
    assert not (moved / output.name).exists()


def test_late_create_race_preserves_independent_winner(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "late-race.json")
    marker = b"independent late-race winner"
    original_open = finalizer_module._open_exclusive_manifest

    def race_open(target: object, parent_guard: int) -> int:
        output.write_bytes(marker)
        return original_open(target, parent_guard)  # type: ignore[arg-type]

    monkeypatch.setattr(finalizer_module, "_open_exclusive_manifest", race_open)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.read_bytes() == marker


@pytest.mark.parametrize(
    "failure",
    ("short-write", "file-fsync", "readback", "postsource", "parent-fsync"),
)
def test_write_readback_fsync_and_postsource_failures_never_leave_valid_manifest(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    output = _manifest_output(tmp_path, f"publication-failure-{failure}.json")
    if failure == "short-write":
        original_write = os.write
        calls = 0

        def short_write(descriptor: int, data: bytes) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(descriptor, data[:19])
            return 0

        monkeypatch.setattr(os, "write", short_write)
    elif failure == "file-fsync":
        original_fsync = os.fsync
        calls = 0

        def fail_first_fsync(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("synthetic Manifest fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(os, "fsync", fail_first_fsync)
    elif failure == "readback":

        def reject_readback(*args: object, **kwargs: object) -> object:
            del args, kwargs
            raise TrustedLocalRightsManifestFinalizationError(
                "synthetic readback failure"
            )

        monkeypatch.setattr(
            finalizer_module,
            "_read_open_created_manifest",
            reject_readback,
        )
    elif failure == "postsource":
        original_capture = finalizer_module._capture_snapshot
        calls = 0

        def fail_third_capture(*args: object, **kwargs: object) -> object:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise TrustedLocalRightsManifestFinalizationError(
                    "synthetic postsource failure"
                )
            return original_capture(*args, **kwargs)

        monkeypatch.setattr(finalizer_module, "_capture_snapshot", fail_third_capture)
    else:

        def reject_parent_fsync(created: object) -> None:
            del created
            raise OSError("synthetic parent fsync failure")

        monkeypatch.setattr(
            finalizer_module,
            "_fsync_parent_directory",
            reject_parent_fsync,
        )

    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    if output.exists():
        with pytest.raises(RealAssetRightsManifestV24Error):
            parse_real_asset_rights_manifest_v2_json(output.read_bytes())


def _fail_on_postwrite_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_capture = finalizer_module._capture_snapshot
    calls = 0

    def fail_third_capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise TrustedLocalRightsManifestFinalizationError(
                "synthetic private postwrite failure"
            )
        return original_capture(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", fail_third_capture)


def test_delete_failure_only_leaves_invalidated_artifact(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "delete-failure.json")
    _fail_on_postwrite_capture(monkeypatch)
    if os.name == "nt":
        monkeypatch.setattr(
            finalizer_module,
            "_delete_open_windows_manifest",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_inspect_created_manifest_name",
            lambda created, identity: (True, False),
        )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.exists()
    with pytest.raises(RealAssetRightsManifestV24Error):
        parse_real_asset_rights_manifest_v2_json(output.read_bytes())


def test_primary_invalidation_and_delete_failure_uses_exact_fd_poison(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "poison-fallback.json")
    _fail_on_postwrite_capture(monkeypatch)
    monkeypatch.setattr(
        finalizer_module,
        "_invalidate_open_manifest",
        lambda descriptor: False,
    )
    if os.name == "nt":
        monkeypatch.setattr(
            finalizer_module,
            "_delete_open_windows_manifest",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_inspect_created_manifest_name",
            lambda created, identity: (True, False),
        )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.read_bytes().startswith(b"\0")
    with pytest.raises(RealAssetRightsManifestV24Error):
        parse_real_asset_rights_manifest_v2_json(output.read_bytes())


def test_total_rollback_failure_requires_explicit_quarantine(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "rollback-quarantine.json")
    _fail_on_postwrite_capture(monkeypatch)
    monkeypatch.setattr(
        finalizer_module,
        "_invalidate_open_manifest",
        lambda descriptor: False,
    )
    monkeypatch.setattr(
        finalizer_module,
        "_emergency_poison_open_manifest",
        lambda descriptor: False,
    )
    if os.name == "nt":
        monkeypatch.setattr(
            finalizer_module,
            "_delete_open_windows_manifest",
            lambda descriptor: False,
        )
    else:
        monkeypatch.setattr(
            finalizer_module,
            "_inspect_created_manifest_name",
            lambda created, identity: (True, False),
        )
    with pytest.raises(TrustedLocalRightsManifestQuarantineRequired, match="quarantine"):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.exists()


@pytest.mark.parametrize("interrupt", (KeyboardInterrupt, SystemExit))
def test_postwrite_base_exception_rolls_back_before_propagation(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    interrupt: type[BaseException],
) -> None:
    output = _manifest_output(tmp_path, f"interrupt-{interrupt.__name__}.json")
    original_capture = finalizer_module._capture_snapshot
    calls = 0

    def interrupt_third_capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise interrupt()
        return original_capture(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", interrupt_third_capture)
    with pytest.raises(interrupt):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    _assert_ordinary_rollback_result(output)


def test_create_time_base_exception_invalidates_partial_manifest(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "create-interrupt.json")
    original_write = os.write
    calls = 0

    def interrupt_first_write(descriptor: int, data: bytes) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise KeyboardInterrupt
        return original_write(descriptor, data)

    monkeypatch.setattr(os, "write", interrupt_first_write)
    with pytest.raises(KeyboardInterrupt):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    _assert_ordinary_rollback_result(output)


def test_replacement_during_failure_is_never_deleted_as_created_manifest(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "replacement-race.json")
    replacement_path = output.parent / "independent-replacement.bin"
    replacement_path.write_bytes(b"independent replacement")
    original_capture = finalizer_module._capture_snapshot
    calls = 0
    replacement_succeeded = False

    def replace_on_third_capture(*args: object, **kwargs: object) -> object:
        nonlocal calls, replacement_succeeded
        calls += 1
        if calls == 3:
            try:
                os.replace(replacement_path, output)
            except PermissionError:
                raise OSError("replacement denied by exact retained handle") from None
            replacement_succeeded = True
        return original_capture(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", replace_on_third_capture)
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    if replacement_succeeded:
        assert output.read_bytes() == b"independent replacement"
    else:
        assert not output.exists()
        assert replacement_path.read_bytes() == b"independent replacement"


@pytest.mark.skipif(os.name == "nt", reason="POSIX exact-pathname rollback rule")
def test_posix_replacement_inode_requires_quarantine_even_after_fd_invalidation(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "posix-replacement-quarantine.json")
    replacement_path = output.parent / "independent-posix-replacement.bin"
    marker = b"independent replacement must never be unlinked"
    replacement_path.write_bytes(marker)
    original_capture = finalizer_module._capture_snapshot
    calls = 0

    def replace_on_third_capture(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 3:
            os.replace(replacement_path, output)
        return original_capture(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_snapshot", replace_on_third_capture)
    with pytest.raises(TrustedLocalRightsManifestQuarantineRequired):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    assert output.read_bytes() == marker


@pytest.mark.skipif(sys.platform != "win32", reason="Windows delete-pending semantics")
def test_windows_delete_pending_is_unconfirmed_when_descriptor_close_fails(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "windows-close-quarantine.json")
    _fail_on_postwrite_capture(monkeypatch)
    original_create = finalizer_module._create_new_manifest
    original_close = os.close
    state: dict[str, int] = {}

    def capture_created(*args: object, **kwargs: object) -> object:
        created = original_create(*args, **kwargs)
        state["descriptor"] = created.descriptor
        return created

    def fail_created_descriptor_close(descriptor: int) -> None:
        if descriptor == state.get("descriptor"):
            raise OSError("synthetic descriptor close failure")
        original_close(descriptor)

    monkeypatch.setattr(finalizer_module, "_create_new_manifest", capture_created)
    monkeypatch.setattr(finalizer_module, "_invalidate_open_manifest", lambda value: False)
    monkeypatch.setattr(
        finalizer_module,
        "_emergency_poison_open_manifest",
        lambda value: False,
    )
    monkeypatch.setattr(
        finalizer_module,
        "_delete_open_windows_manifest",
        lambda value: True,
    )
    monkeypatch.setattr(os, "close", fail_created_descriptor_close)
    try:
        with pytest.raises(TrustedLocalRightsManifestQuarantineRequired):
            finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    finally:
        descriptor = state.get("descriptor")
        if descriptor is not None:
            original_close(descriptor)
        output.unlink(missing_ok=True)


def test_commit_guard_close_failure_maps_to_quarantine_required(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path, "guard-close-quarantine.json")
    original_close = finalizer_module._close_parent_guard

    def close_then_fail(created: object) -> None:
        original_close(created)  # type: ignore[arg-type]
        raise OSError("synthetic CloseHandle completion failure")

    monkeypatch.setattr(finalizer_module, "_close_parent_guard", close_then_fail)
    with pytest.raises(TrustedLocalRightsManifestQuarantineRequired):
        finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)


def test_verify_existing_manifest_rejects_file_and_nonfile_reserved_digest_aliases(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path)
    finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    original_read = finalizer_module._read_manifest
    decision_digest = _sha256(closure.paths.decision.read_bytes())
    collisions = (
        closure.decision_closure.request.policy_document_sha256,
        closure.decision_closure.request.review_a_record_sha256,
        closure.decision_closure.pack.objects[0].provenance_record_sha256,
        closure.decision_closure.pack.objects[0].technical_record_sha256,
        decision_digest,
    )
    for collision in collisions:
        def read_with_collision(
            path: Path,
            collision_digest: str = collision,
        ) -> tuple[object, object]:
            manifest, seal = original_read(path)
            return manifest, replace(seal, sha256=collision_digest)

        monkeypatch.setattr(finalizer_module, "_read_manifest", read_with_collision)
        with pytest.raises(TrustedLocalRightsManifestFinalizationError):
            verify_manifest(closure.paths, output)


def test_verify_is_historical_zero_write_and_rejects_manifest_tampering(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    output = _manifest_output(tmp_path)
    manifest = finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)
    before = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert verify_manifest(closure.paths, output) == manifest
    after = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before

    payload = manifest.model_dump(mode="json")
    payload["unknown"] = True
    output.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError):
        verify_manifest(closure.paths, output)


def test_verify_rejects_manifest_inside_any_source_trust_area(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
) -> None:
    source = _manifest_output(tmp_path)
    finalize_manifest(closure.paths, source, manifest_at=MANIFEST_AT)
    nested_parent = closure.paths.decision.parent / "nested-manifest"
    nested_parent.mkdir()
    intersecting = nested_parent / "manifest.json"
    intersecting.write_bytes(source.read_bytes())
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="trust area"):
        verify_manifest(closure.paths, intersecting)


def test_verify_rejects_a_pure_verifier_returning_a_different_manifest(
    closure: SyntheticManifestClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _manifest_output(tmp_path)
    manifest = finalize_manifest(closure.paths, output, manifest_at=MANIFEST_AT)

    def different_manifest(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return manifest.model_copy(update={"manifest_at": DECISION_AT})

    monkeypatch.setattr(
        finalizer_module,
        "verify_real_asset_rights_manifest_closure_v2",
        different_manifest,
    )
    with pytest.raises(TrustedLocalRightsManifestFinalizationError, match="different"):
        verify_manifest(closure.paths, output)


def test_cli_catches_unknown_base_exception_without_private_disclosure(
    closure: SyntheticManifestClosure,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private = "PRIVATE-BASE-EXCEPTION-MARKER"

    class PrivateInterrupt(BaseException):
        pass

    def interrupt(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PrivateInterrupt(private)

    monkeypatch.setattr(finalizer_module, "inspect_manifest_ready", interrupt)
    argv = [
        "inspect-manifest-ready",
        *_cli_args(closure.paths),
        "--manifest-at",
        MANIFEST_AT,
    ]
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert private not in captured.err
    summary = json.loads(captured.err)
    assert summary == {
        "current_gate": "HUMAN_GATE",
        "eligible_for_real_generation": False,
        "execution_authorized": False,
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "rights_manifest_created": False,
        "status": "FAILED_CLOSED",
    }


@pytest.mark.parametrize("duplicate_flag", ("--pack-root", "--decision", "--manifest-at"))
def test_cli_rejects_duplicate_singleton_flags_before_dispatch_without_disclosure(
    closure: SyntheticManifestClosure,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    duplicate_flag: str,
) -> None:
    private = "PRIVATE-DUPLICATE-FLAG-MARKER"
    calls = 0

    def dispatched(*args: object, **kwargs: object) -> None:
        nonlocal calls
        del args, kwargs
        calls += 1

    monkeypatch.setattr(finalizer_module, "inspect_manifest_ready", dispatched)
    argv = [
        "inspect-manifest-ready",
        *_cli_args(closure.paths),
        "--manifest-at",
        MANIFEST_AT,
        duplicate_flag,
        private,
    ]
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert calls == 0
    assert captured.out == ""
    assert private not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"


def test_cli_rejects_abbreviated_flags_before_dispatch_without_disclosure(
    closure: SyntheticManifestClosure,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private = "PRIVATE-ABBREVIATION-MARKER"
    calls = 0

    def dispatched(*args: object, **kwargs: object) -> None:
        nonlocal calls
        del args, kwargs
        calls += 1

    monkeypatch.setattr(finalizer_module, "inspect_manifest_ready", dispatched)
    argv = [
        "inspect-manifest-ready",
        *_cli_args(closure.paths),
        "--manifest-a",
        private,
    ]
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert calls == 0
    assert captured.out == ""
    assert private not in captured.err
    assert json.loads(captured.err)["status"] == "FAILED_CLOSED"
