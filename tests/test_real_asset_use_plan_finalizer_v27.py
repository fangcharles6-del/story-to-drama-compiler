from __future__ import annotations

import ast
import inspect
import json
import os
import stat
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints

import pytest
from test_real_asset_rights_manifest_finalizer_v25 import (
    MANIFEST_AT,
    SyntheticManifestClosure,
    _canonical_document,
)
from test_real_asset_rights_manifest_finalizer_v25 import (
    closure as _manifest_closure_fixture,
)

import sdc.real_asset_use_plan_finalizer_v27 as finalizer_module
from sdc.real_asset_rights_manifest_finalizer_v25 import finalize_manifest
from sdc.real_asset_rights_manifest_v24 import CreativeSampleRealAssetRightsManifestV2
from sdc.real_asset_use_plan_finalizer_v27 import (
    TrustedLocalUsePlanFinalizationError,
    TrustedLocalUsePlanPaths,
    TrustedLocalUsePlanQuarantineRequired,
    UsePlanReadinessV27,
    finalize_use_plan,
    inspect_use_plan_ready,
    main,
    verify_use_plan,
)
from sdc.real_asset_use_plan_v26 import (
    USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
    CreativeSampleRealAssetUsePlanV1,
    RealAssetUsePlanV26Error,
    parse_real_asset_use_plan_v1_json,
)


@dataclass(frozen=True)
class SyntheticUsePlanClosure:
    paths: TrustedLocalUsePlanPaths
    manifest_closure: SyntheticManifestClosure
    manifest: CreativeSampleRealAssetRightsManifestV2
    manifest_path: Path


@pytest.fixture
def use_plan_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> SyntheticUsePlanClosure:
    factory = _manifest_closure_fixture.__wrapped__
    manifest_closure: SyntheticManifestClosure = factory(tmp_path, monkeypatch)
    manifest_parent = (tmp_path / "rights-manifest-area").resolve()
    manifest_parent.mkdir()
    manifest_path = manifest_parent / "rights-manifest-v2.json"
    manifest = finalize_manifest(
        manifest_closure.paths,
        manifest_path,
        manifest_at=MANIFEST_AT,
    )
    return SyntheticUsePlanClosure(
        paths=TrustedLocalUsePlanPaths(
            manifest_sources=manifest_closure.paths,
            rights_manifest=manifest_path.resolve(),
        ),
        manifest_closure=manifest_closure,
        manifest=manifest,
        manifest_path=manifest_path.resolve(),
    )


def _plan_output(tmp_path: Path, name: str = "real-asset-use-plan-v1.json") -> Path:
    parent = (tmp_path / "use-plan-area").resolve()
    parent.mkdir(exist_ok=True)
    return parent / name


def _assert_ordinary_rollback_result(output: Path) -> None:
    if sys.platform == "win32":
        assert not output.exists()
        return
    assert stat.S_ISREG(output.lstat().st_mode)
    raw = output.read_bytes()
    assert raw == b"" or raw.startswith(b"\0")
    with pytest.raises(RealAssetUsePlanV26Error):
        parse_real_asset_use_plan_v1_json(raw)


def test_strict_absence_proof_only_accepts_file_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / "strictly-missing.json"
    assert finalizer_module._strict_path_is_absent(missing)
    missing.write_bytes(b"")
    assert not finalizer_module._strict_path_is_absent(missing)

    def deny_lstat(path: Path) -> os.stat_result:
        del path
        raise PermissionError("synthetic metadata denial")

    monkeypatch.setattr(Path, "lstat", deny_lstat)
    assert not finalizer_module._strict_path_is_absent(missing)


def _cli_args(paths: TrustedLocalUsePlanPaths) -> list[str]:
    manifest = paths.manifest_sources
    request = manifest.decision_inputs.request_inputs
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
            "--qualification-request",
            str(manifest.decision_inputs.request),
            "--qualifier-ref",
            str(manifest.decision_inputs.qualifier_ref),
            "--qualification-instruction",
            str(manifest.decision_inputs.qualifier_decision_record),
            "--qualification-decision",
            str(manifest.decision),
            "--rights-manifest-file",
            str(paths.rights_manifest),
        )
    )
    return values


def _assert_zero_authority(plan: CreativeSampleRealAssetUsePlanV1) -> None:
    assert plan.status == "USE_PLAN_CANDIDATE_CREATED"
    assert plan.current_gate == "HUMAN_GATE"
    assert plan.provider_state == "NOT_AUTHORIZED"
    assert plan.eligible_for_separate_use_scope_review is True
    assert plan.eligible_for_separate_provider_proposal is False
    assert plan.eligible_for_separate_provider_approval is False
    assert plan.provider_approval_granted is False
    assert plan.eligible_for_real_generation is False
    assert plan.generation_authorized is False
    assert plan.execution_authorized is False
    assert plan.publication_authorized is False
    assert plan.remote_processing_allowed is False
    assert plan.retention_allowed is False
    assert plan.training_allowed is False
    assert plan.publication_allowed is False
    assert plan.authorized_attempts == plan.authorized_cost_cny == 0
    assert plan.posts_allowed == plan.provider_requests == 0


def test_exact_twenty_nine_and_thirty_source_snapshots(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    assert len(finalizer_module._all_use_plan_source_paths(normalized)) == 29
    snapshot = finalizer_module._capture_use_plan_snapshot(normalized)
    assert len(snapshot.files) == 28
    assert snapshot.manifest_snapshot.manifest == use_plan_closure.manifest

    readiness = inspect_use_plan_ready(normalized)
    output = _plan_output(tmp_path)
    finalize_use_plan(
        normalized,
        output,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    plan_path = finalizer_module._validate_existing_use_plan(output, paths=normalized)
    plan_snapshot = finalizer_module._capture_use_plan_snapshot(
        normalized,
        use_plan_path=plan_path,
    )
    assert len(plan_snapshot.files) == 29
    assert plan_snapshot.use_plan is not None


def test_inspect_builds_once_between_two_complete_captures_and_writes_nothing(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_capture = finalizer_module._capture_use_plan_snapshot
    original_builder = finalizer_module.build_real_asset_use_plan_v1

    def capture(*args: object, **kwargs: object) -> object:
        result = original_capture(*args, **kwargs)
        events.append("capture")
        return result

    def build(*args: object, **kwargs: object) -> CreativeSampleRealAssetUsePlanV1:
        events.append("build")
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_use_plan_snapshot", capture)
    monkeypatch.setattr(finalizer_module, "build_real_asset_use_plan_v1", build)
    before = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    after = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert events == ["capture", "build", "capture"]
    assert readiness.status == "READY_FOR_USE_PLAN_FINALIZATION"
    assert readiness.plan_id.startswith("real_asset_use_plan_v1_")
    assert len(readiness.plan_sha256) == 64
    assert before == after


def test_finalize_anchor_create_new_and_historical_verify(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path)
    finalized = finalize_use_plan(
        use_plan_closure.paths,
        output,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    assert output.read_bytes() == _canonical_document(finalized)
    assert parse_real_asset_use_plan_v1_json(output.read_bytes()) == finalized
    _assert_zero_authority(finalized)
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600

    verified = verify_use_plan(use_plan_closure.paths, output)
    assert verified == finalized


def test_finalize_event_order_is_anchor_bound_before_output_open(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path, "ordered-use-plan.json")
    events: list[str] = []
    original_capture = finalizer_module._capture_use_plan_snapshot
    original_build = finalizer_module._build_use_plan
    original_create = finalizer_module._create_new_artifact
    original_commit = finalizer_module._commit_created_artifact

    def capture(*args: object, **kwargs: object) -> object:
        result = original_capture(*args, **kwargs)
        events.append("capture")
        return result

    def build(*args: object, **kwargs: object) -> CreativeSampleRealAssetUsePlanV1:
        events.append("build")
        return original_build(*args, **kwargs)

    def create(*args: object, **kwargs: object) -> object:
        events.append("create")
        return original_create(*args, **kwargs)

    def commit(*args: object, **kwargs: object) -> None:
        events.append("commit")
        original_commit(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_use_plan_snapshot", capture)
    monkeypatch.setattr(finalizer_module, "_build_use_plan", build)
    monkeypatch.setattr(finalizer_module, "_create_new_artifact", create)
    monkeypatch.setattr(finalizer_module, "_commit_created_artifact", commit)
    finalize_use_plan(
        use_plan_closure.paths,
        output,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    assert events == ["capture", "build", "capture", "create", "capture", "commit"]


@pytest.mark.parametrize("wrong_member", ("id", "sha", "pair"))
def test_expected_anchor_is_comparison_only_and_mismatch_never_opens_output(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrong_member: str,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path, f"mismatch-{wrong_member}.json")
    expected_id = readiness.plan_id
    expected_sha = readiness.plan_sha256
    if wrong_member in {"id", "pair"}:
        expected_id = f"{expected_id[:-1]}{'0' if expected_id[-1] != '0' else '1'}"
    if wrong_member in {"sha", "pair"}:
        expected_sha = f"{expected_sha[:-1]}{'0' if expected_sha[-1] != '0' else '1'}"

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("anchor mismatch must fail before output open")

    monkeypatch.setattr(finalizer_module, "_create_new_artifact", forbidden)
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalize_use_plan(
            use_plan_closure.paths,
            output,
            expected_plan_id=expected_id,
            expected_plan_sha256=expected_sha,
        )
    assert not output.exists()


def test_malformed_api_anchor_fails_before_any_private_path_open(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _plan_output(tmp_path)

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("malformed guards must be checked first")

    monkeypatch.setattr(finalizer_module, "_normalize_use_plan_paths", forbidden)
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalize_use_plan(
            use_plan_closure.paths,
            output,
            expected_plan_id="not-an-id",
            expected_plan_sha256="not-a-sha",
        )


def test_existing_output_is_never_overwritten(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path)
    marker = b"do not overwrite"
    output.write_bytes(marker)
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalize_use_plan(
            use_plan_closure.paths,
            output,
            expected_plan_id=readiness.plan_id,
            expected_plan_sha256=readiness.plan_sha256,
        )
    assert output.read_bytes() == marker


def test_failure_after_create_rolls_back_exact_created_object(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path)
    original_capture = finalizer_module._capture_use_plan_snapshot
    captures = 0

    def capture(*args: object, **kwargs: object) -> object:
        nonlocal captures
        captures += 1
        if captures == 3:
            raise TrustedLocalUsePlanFinalizationError("synthetic post-write drift")
        return original_capture(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_use_plan_snapshot", capture)
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalize_use_plan(
            use_plan_closure.paths,
            output,
            expected_plan_id=readiness.plan_id,
            expected_plan_sha256=readiness.plan_sha256,
        )
    _assert_ordinary_rollback_result(output)


def test_base_exception_between_create_and_holder_is_always_rolled_back(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    original_holder = finalizer_module._CreatedArtifact
    failures: tuple[BaseException, ...] = (
        RuntimeError("synthetic holder failure"),
        KeyboardInterrupt("synthetic interrupt"),
    )
    for ordinal, failure in enumerate(failures):
        output = _plan_output(tmp_path, f"holder-gap-{ordinal}.json")

        def fail_holder(
            *args: object,
            _failure: BaseException = failure,
            **kwargs: object,
        ) -> None:
            del args, kwargs
            raise _failure

        with monkeypatch.context() as scoped:
            scoped.setattr(finalizer_module, "_CreatedArtifact", fail_holder)
            expected_error = (
                TrustedLocalUsePlanFinalizationError
                if isinstance(failure, RuntimeError)
                else KeyboardInterrupt
            )
            with pytest.raises(expected_error):
                finalize_use_plan(
                    use_plan_closure.paths,
                    output,
                    expected_plan_id=readiness.plan_id,
                    expected_plan_sha256=readiness.plan_sha256,
                )
        assert finalizer_module._CreatedArtifactHolder is original_holder
        _assert_ordinary_rollback_result(output)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows raw HANDLE fault injection")
def test_windows_raw_handle_conversion_base_exceptions_are_poisoned_and_deleted(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    failures: tuple[BaseException, ...] = (
        RuntimeError("synthetic conversion failure"),
        KeyboardInterrupt("synthetic conversion interrupt"),
    )
    for ordinal, failure in enumerate(failures):
        output = _plan_output(tmp_path, f"raw-handle-gap-{ordinal}.json")

        def fail_conversion(
            *args: object,
            _failure: BaseException = failure,
            **kwargs: object,
        ) -> None:
            del args, kwargs
            raise _failure

        with monkeypatch.context() as scoped:
            scoped.setattr(
                finalizer_module._windows_msvcrt,
                "open_osfhandle",
                fail_conversion,
            )
            expected_error = (
                TrustedLocalUsePlanFinalizationError
                if isinstance(failure, RuntimeError)
                else KeyboardInterrupt
            )
            with pytest.raises(expected_error):
                finalize_use_plan(
                    use_plan_closure.paths,
                    output,
                    expected_plan_id=readiness.plan_id,
                    expected_plan_sha256=readiness.plan_sha256,
                )
        assert not os.path.lexists(output)


def test_open_call_store_gaps_quarantine_all_base_exceptions_and_remnants(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    snapshot = finalizer_module._capture_use_plan_snapshot(normalized)
    candidate = finalizer_module._build_use_plan(snapshot)
    original_open = finalizer_module._open_exclusive_artifact
    failures: tuple[BaseException, ...] = (
        RuntimeError("synthetic outer call-store failure"),
        KeyboardInterrupt("synthetic outer call-store interrupt"),
        SystemExit("synthetic outer call-store exit"),
    )
    for ordinal, failure in enumerate(failures):
        output = _plan_output(tmp_path, f"outer-call-store-{ordinal}.json")
        sibling = output.with_name(f"outer-call-store-remnant-{ordinal}.json")
        target = finalizer_module._validate_use_plan_output(output, paths=normalized)
        retained: list[int] = []
        renamed = sys.platform != "win32" and isinstance(failure, KeyboardInterrupt)

        def fail_after_open(
            opened_target: object,
            parent_guard: int,
            attempt_state: object,
            *,
            _failure: BaseException = failure,
            _retained: list[int] = retained,
            _renamed: bool = renamed,
            _output: Path = output,
            _sibling: Path = sibling,
        ) -> int:
            descriptor = original_open(opened_target, parent_guard, attempt_state)
            _retained.append(descriptor)
            if _renamed:
                _output.rename(_sibling)
            raise _failure

        try:
            with monkeypatch.context() as scoped:
                scoped.setattr(
                    finalizer_module,
                    "_open_exclusive_artifact",
                    fail_after_open,
                )
                with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                    finalizer_module._create_new_artifact(
                        target,
                        candidate,
                        parser=parse_real_asset_use_plan_v1_json,
                        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                        field="Use Plan",
                    )
            assert len(retained) == 1
            assert os.fstat(retained[0]).st_size == 0
        finally:
            for descriptor in retained:
                os.close(descriptor)
        remnant = sibling if renamed else output
        if renamed:
            assert not output.exists()
        assert remnant.read_bytes() == b""
        with pytest.raises(RealAssetUsePlanV26Error):
            parse_real_asset_use_plan_v1_json(remnant.read_bytes())
        remnant.unlink()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX openat fault injection")
@pytest.mark.parametrize(
    ("failure", "suffix"),
    (
        (MemoryError("synthetic inner call-store memory failure"), "memory"),
        (PermissionError("synthetic inner call-store permission failure"), "permission"),
    ),
)
def test_posix_inner_open_call_store_gap_requires_quarantine(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    suffix: str,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, f"posix-inner-call-store-{suffix}.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)
    original_call = finalizer_module._call_posix_exclusive_create
    retained: list[int] = []

    def fail_after_native_open(*args: object, **kwargs: object) -> int:
        descriptor = original_call(*args, **kwargs)
        retained.append(descriptor)
        raise failure

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(
                finalizer_module,
                "_call_posix_exclusive_create",
                fail_after_native_open,
            )
            with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                finalizer_module._create_new_artifact(
                    target,
                    candidate,
                    parser=parse_real_asset_use_plan_v1_json,
                    maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                    field="Use Plan",
                )
        assert len(retained) == 1
        assert os.fstat(retained[0]).st_size == 0
    finally:
        for descriptor in retained:
            os.close(descriptor)
    assert output.read_bytes() == b""
    output.unlink()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows CreateFileW fault injection")
def test_windows_createfile_call_store_gap_requires_quarantine(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, "windows-createfile-call-store.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)
    original_call = finalizer_module._call_windows_create_file
    retained: list[int] = []

    def fail_after_createfile(*args: object, **kwargs: object) -> int:
        raw_handle = original_call(*args, **kwargs)
        retained.append(raw_handle)
        raise KeyboardInterrupt("synthetic CreateFileW call-store interrupt")

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(
                finalizer_module,
                "_call_windows_create_file",
                fail_after_createfile,
            )
            with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                finalizer_module._create_new_artifact(
                    target,
                    candidate,
                    parser=parse_real_asset_use_plan_v1_json,
                    maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                    field="Use Plan",
                )
        assert len(retained) == 1
        finalizer_module._rollback_raw_windows_handle(target, retained.pop())
        assert finalizer_module._strict_path_is_absent(output)
    finally:
        for raw_handle in retained:
            finalizer_module._manifest_boundary._close_windows_handle(raw_handle)


def test_file_exists_is_winner_only_before_open_and_rolls_back_after_open(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, "post-open-file-exists.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)

    def fail_after_open(descriptor: int) -> None:
        del descriptor
        raise FileExistsError("synthetic post-open failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(finalizer_module, "_assert_owner_only_descriptor", fail_after_open)
        with pytest.raises(TrustedLocalUsePlanFinalizationError) as raised:
            finalizer_module._create_new_artifact(
                target,
                candidate,
                parser=parse_real_asset_use_plan_v1_json,
                maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                field="Use Plan",
            )
    assert not isinstance(raised.value, TrustedLocalUsePlanQuarantineRequired)
    _assert_ordinary_rollback_result(output)

    winner_output = _plan_output(tmp_path, "independent-winner.json")
    winner_target = finalizer_module._validate_use_plan_output(
        winner_output,
        paths=normalized,
    )
    marker = b"independent winner"

    def report_independent_winner(*args: object, **kwargs: object) -> int:
        del args, kwargs
        winner_output.write_bytes(marker)
        raise finalizer_module._IndependentArtifactCreateWinner(str(winner_output))

    with monkeypatch.context() as scoped:
        scoped.setattr(
            finalizer_module,
            "_open_exclusive_artifact",
            report_independent_winner,
        )
        with pytest.raises(TrustedLocalUsePlanFinalizationError) as winner_raised:
            finalizer_module._create_new_artifact(
                winner_target,
                candidate,
                parser=parse_real_asset_use_plan_v1_json,
                maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                field="Use Plan",
            )
    assert not isinstance(winner_raised.value, TrustedLocalUsePlanQuarantineRequired)
    assert winner_output.read_bytes() == marker
    winner_output.unlink()

    guard_output = _plan_output(tmp_path, "parent-close-after-rollback.json")
    guard_target = finalizer_module._validate_use_plan_output(
        guard_output,
        paths=normalized,
    )
    retained_guards: list[int] = []
    original_os_close = finalizer_module.os.close
    original_windows_close = finalizer_module._manifest_boundary._close_windows_handle

    def safely_rolled_back_then_fail(
        target: object,
        parent_guard: int,
        attempt_state: object,
    ) -> int:
        del target
        retained_guards.append(parent_guard)
        attempt_state.native_call_entered = True
        attempt_state.rollback_confirmed = True
        raise RuntimeError("synthetic failure after exact file rollback")

    def fail_parent_close(handle: int) -> None:
        if retained_guards and handle == retained_guards[-1]:
            raise OSError("synthetic parent close failure")
        if sys.platform == "win32":
            original_windows_close(handle)
        else:
            original_os_close(handle)

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(
                finalizer_module,
                "_open_exclusive_artifact",
                safely_rolled_back_then_fail,
            )
            if sys.platform == "win32":
                scoped.setattr(
                    finalizer_module._manifest_boundary,
                    "_close_windows_handle",
                    fail_parent_close,
                )
            else:
                scoped.setattr(finalizer_module.os, "close", fail_parent_close)
            with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                finalizer_module._create_new_artifact(
                    guard_target,
                    candidate,
                    parser=parse_real_asset_use_plan_v1_json,
                    maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                    field="Use Plan",
                )
        assert len(retained_guards) == 1
    finally:
        for guard in retained_guards:
            if sys.platform == "win32":
                finalizer_module._manifest_boundary._close_windows_handle(guard)
            else:
                os.close(guard)


def test_commit_parent_close_base_exceptions_rollback_before_quarantine(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    original_close = finalizer_module._close_parent_guard
    failures: tuple[BaseException, ...] = (
        RuntimeError("synthetic commit parent-close failure"),
        KeyboardInterrupt("synthetic commit parent-close interrupt"),
        SystemExit("synthetic commit parent-close exit"),
    )
    for ordinal, failure in enumerate(failures):
        output = _plan_output(tmp_path, f"commit-parent-close-{ordinal}.json")
        target = finalizer_module._validate_use_plan_output(output, paths=normalized)
        created = finalizer_module._create_new_artifact(
            target,
            candidate,
            parser=parse_real_asset_use_plan_v1_json,
            maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
            field="Use Plan",
        )

        def close_then_fail(
            artifact: object,
            *,
            _failure: BaseException = failure,
        ) -> None:
            original_close(artifact)
            raise _failure

        with monkeypatch.context() as scoped:
            scoped.setattr(finalizer_module, "_close_parent_guard", close_then_fail)
            with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                finalizer_module._commit_created_artifact(
                    created,
                    candidate,
                    parser=parse_real_asset_use_plan_v1_json,
                    maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                    field="Use Plan",
                )
        assert created.closed
        assert created.parent_guard_closed
        assert created.parent_guard_close_uncertain
        _assert_ordinary_rollback_result(output)

    normal_output = _plan_output(tmp_path, "commit-parent-close-normal.json")
    normal_target = finalizer_module._validate_use_plan_output(
        normal_output,
        paths=normalized,
    )
    normal_created = finalizer_module._create_new_artifact(
        normal_target,
        candidate,
        parser=parse_real_asset_use_plan_v1_json,
        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
        field="Use Plan",
    )
    finalizer_module._commit_created_artifact(
        normal_created,
        candidate,
        parser=parse_real_asset_use_plan_v1_json,
        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
        field="Use Plan",
    )
    assert normal_created.closed
    assert normal_created.parent_guard_closed
    assert not normal_created.parent_guard_close_uncertain
    assert parse_real_asset_use_plan_v1_json(normal_output.read_bytes()) == candidate


def test_commit_descriptor_close_uncertainty_never_reuses_the_fd(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    cases: tuple[tuple[str, BaseException], ...] = (
        ("before", RuntimeError("synthetic close-before-side-effect failure")),
        ("after-ki", KeyboardInterrupt("synthetic close-after-side-effect interrupt")),
        ("after-exit", SystemExit("synthetic close-after-side-effect exit")),
    )
    for ordinal, (mode, failure) in enumerate(cases):
        output = _plan_output(tmp_path, f"commit-descriptor-close-{ordinal}.json")
        target = finalizer_module._validate_use_plan_output(output, paths=normalized)
        created = finalizer_module._create_new_artifact(
            target,
            candidate,
            parser=parse_real_asset_use_plan_v1_json,
            maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
            field="Use Plan",
        )
        original_close = finalizer_module.os.close
        output_close_calls: list[int] = []
        invalidation_calls: list[int] = []

        def uncertain_close(
            descriptor: int,
            *,
            _mode: str = mode,
            _failure: BaseException = failure,
            _created: object = created,
            _original_close: object = original_close,
            _output_close_calls: list[int] = output_close_calls,
        ) -> None:
            if descriptor != _created.descriptor:
                _original_close(descriptor)
                return
            _output_close_calls.append(descriptor)
            if _mode != "before":
                _original_close(descriptor)
            raise _failure

        def forbidden_invalidation(
            descriptor: int,
            _invalidation_calls: list[int] = invalidation_calls,
        ) -> bool:
            _invalidation_calls.append(descriptor)
            return False

        try:
            with monkeypatch.context() as scoped:
                scoped.setattr(finalizer_module.os, "close", uncertain_close)
                scoped.setattr(
                    finalizer_module._manifest_boundary,
                    "_invalidate_open_manifest",
                    forbidden_invalidation,
                )
                with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                    finalizer_module._commit_created_artifact(
                        created,
                        candidate,
                        parser=parse_real_asset_use_plan_v1_json,
                        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                        field="Use Plan",
                    )
                with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                    finalizer_module._rollback_created_artifact(created)
            assert output_close_calls == [created.descriptor]
            assert invalidation_calls == []
            assert created.descriptor_close_uncertain
            assert not created.closed
        finally:
            if mode == "before":
                original_close(created.descriptor)
        assert parse_real_asset_use_plan_v1_json(output.read_bytes()) == candidate
        output.unlink()

    normal_output = _plan_output(tmp_path, "commit-descriptor-close-normal.json")
    normal_target = finalizer_module._validate_use_plan_output(
        normal_output,
        paths=normalized,
    )
    normal_created = finalizer_module._create_new_artifact(
        normal_target,
        candidate,
        parser=parse_real_asset_use_plan_v1_json,
        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
        field="Use Plan",
    )
    finalizer_module._commit_created_artifact(
        normal_created,
        candidate,
        parser=parse_real_asset_use_plan_v1_json,
        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
        field="Use Plan",
    )
    assert normal_created.closed
    assert not normal_created.descriptor_close_uncertain
    assert parse_real_asset_use_plan_v1_json(normal_output.read_bytes()) == candidate


def test_rollback_descriptor_close_state_exceptions_never_reuse_the_fd(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    original_record = finalizer_module._record_descriptor_closed
    cases: tuple[tuple[str, BaseException], ...] = (
        ("before-record", KeyboardInterrupt("synthetic post-close state interrupt")),
        ("after-clear", SystemExit("synthetic post-clear state exit")),
    )
    for ordinal, (mode, failure) in enumerate(cases):
        output = _plan_output(tmp_path, f"rollback-close-state-{ordinal}.json")
        target = finalizer_module._validate_use_plan_output(output, paths=normalized)
        created = finalizer_module._create_new_artifact(
            target,
            candidate,
            parser=parse_real_asset_use_plan_v1_json,
            maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
            field="Use Plan",
        )

        def fail_state_record(
            artifact: object,
            *,
            _mode: str = mode,
            _failure: BaseException = failure,
        ) -> None:
            if _mode == "after-clear":
                original_record(artifact)
            raise _failure

        with monkeypatch.context() as scoped:
            scoped.setattr(
                finalizer_module,
                "_record_descriptor_closed",
                fail_state_record,
            )
            with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                finalizer_module._rollback_created_artifact(created)
        if mode == "before-record":
            assert not created.closed
            assert created.descriptor_close_uncertain
        else:
            assert created.closed
            assert not created.descriptor_close_uncertain

        descriptor_operations: list[str] = []

        def forbidden(
            *args: object,
            _operations: list[str] = descriptor_operations,
            **kwargs: object,
        ) -> None:
            del args, kwargs
            _operations.append("called")
            raise AssertionError("closed descriptor was reused")

        with monkeypatch.context() as scoped:
            scoped.setattr(finalizer_module.os, "fstat", forbidden)
            scoped.setattr(finalizer_module.os, "close", forbidden)
            scoped.setattr(
                finalizer_module._manifest_boundary,
                "_invalidate_open_manifest",
                forbidden,
            )
            if mode == "before-record":
                with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
                    finalizer_module._rollback_created_artifact(created)
            else:
                finalizer_module._rollback_created_artifact(created)
        assert descriptor_operations == []
        _assert_ordinary_rollback_result(output)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX dir_fd reuse semantics")
def test_rollback_never_uses_an_uncertain_parent_guard_as_dir_fd(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, "uncertain-parent-dir-fd.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)
    created = finalizer_module._create_new_artifact(
        target,
        candidate,
        parser=parse_real_asset_use_plan_v1_json,
        maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
        field="Use Plan",
    )
    finalizer_module._close_parent_guard(created)
    created.parent_guard_close_uncertain = True
    original_stat = finalizer_module.os.stat
    guarded_stat_calls: list[int] = []

    def trap_reused_dir_fd(*args: object, **kwargs: object) -> os.stat_result:
        if kwargs.get("dir_fd") == created.parent_guard:
            guarded_stat_calls.append(created.parent_guard)
            raise AssertionError("uncertain parent guard was reused as dir_fd")
        return original_stat(*args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(finalizer_module.os, "stat", trap_reused_dir_fd)
        with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
            finalizer_module._rollback_created_artifact(created, close_parent=False)
    assert guarded_stat_calls == []
    _assert_ordinary_rollback_result(output)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX native errno classification")
def test_posix_native_oserror_without_a_descriptor_requires_quarantine(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, "posix-native-oserror.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)
    original_open = finalizer_module.os.open

    def deny_create(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if flags & os.O_CREAT:
            raise PermissionError("synthetic native access denial")
        return original_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(finalizer_module.os, "open", deny_create)
        scoped.setattr(
            finalizer_module.os,
            "supports_dir_fd",
            {*os.supports_dir_fd, deny_create},
        )
        with pytest.raises(TrustedLocalUsePlanQuarantineRequired):
            finalizer_module._create_new_artifact(
                target,
                candidate,
                parser=parse_real_asset_use_plan_v1_json,
                maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                field="Use Plan",
            )
    assert not output.exists()


def test_verify_uses_full_pure_closure_between_two_thirty_source_captures(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path)
    finalize_use_plan(
        use_plan_closure.paths,
        output,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    events: list[str] = []
    original_capture = finalizer_module._capture_use_plan_snapshot
    original_verify = finalizer_module.verify_real_asset_use_plan_closure_v1

    def capture(*args: object, **kwargs: object) -> object:
        result = original_capture(*args, **kwargs)
        assert len(result.files) == 29
        events.append("capture-30")
        return result

    def verify(*args: object, **kwargs: object) -> object:
        events.append("pure-verify")
        return original_verify(*args, **kwargs)

    monkeypatch.setattr(finalizer_module, "_capture_use_plan_snapshot", capture)
    monkeypatch.setattr(finalizer_module, "verify_real_asset_use_plan_closure_v1", verify)
    assert verify_use_plan(use_plan_closure.paths, output).plan_id == readiness.plan_id
    assert events == ["capture-30", "pure-verify", "capture-30"]


def test_plan_policy_and_all_normative_plan_sha256_values_are_reserved(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    snapshot = finalizer_module._capture_use_plan_snapshot(normalized)
    candidate = finalizer_module._build_use_plan(snapshot)
    normative = finalizer_module._normative_use_plan_sha256_values(candidate)
    reserved = finalizer_module._reserved_use_plan_snapshot_digests(snapshot)
    assert USE_PLAN_V1_POLICY_DOCUMENT_SHA256 in normative
    assert USE_PLAN_V1_POLICY_DOCUMENT_SHA256 in reserved
    assert {
        candidate.plan_policy_document_sha256,
        candidate.baseline.pilot_spec_payload_sha256,
        candidate.baseline.pilot_spec_document_sha256,
        candidate.baseline.pilot_compilation_document_sha256,
        candidate.baseline.intake_template_document_sha256,
        candidate.baseline.projection_sha256,
        candidate.planned_spec_payload_sha256,
        candidate.planned_spec_document_sha256,
        candidate.planned_compilation_document_sha256,
    } <= normative

    with monkeypatch.context() as scoped:
        scoped.setattr(
            finalizer_module,
            "_sha256",
            lambda value: USE_PLAN_V1_POLICY_DOCUMENT_SHA256,
        )
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalizer_module._assert_use_plan_candidate(candidate, snapshot=snapshot)
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    output = _plan_output(tmp_path, "policy-alias-plan.json")
    finalized = finalize_use_plan(
        use_plan_closure.paths,
        output,
        expected_plan_id=readiness.plan_id,
        expected_plan_sha256=readiness.plan_sha256,
    )
    original_file_seal = finalizer_module._file_seal

    def aliased_plan_seal(source: object) -> object:
        seal = original_file_seal(source)
        if seal.path == output:
            return replace(seal, sha256=finalized.plan_policy_document_sha256)
        return seal

    monkeypatch.setattr(finalizer_module, "_file_seal", aliased_plan_seal)
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        verify_use_plan(use_plan_closure.paths, output)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows parent HANDLE semantics")
def test_windows_parent_guard_binds_exact_volume_and_file_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = (tmp_path / "windows-parent-identity").resolve()
    parent.mkdir()
    info = parent.lstat()
    target = finalizer_module._OutputTarget(
        path=parent / "new-plan.json",
        parent=parent,
        parent_physical_identity=(info.st_dev, info.st_ino),
    )
    guard = finalizer_module._acquire_parent_guard(target)
    try:
        assert finalizer_module._windows_handle_identity(guard[0]) == (
            info.st_dev,
            info.st_ino,
        )
    finally:
        finalizer_module._manifest_boundary._close_windows_handle(guard[0])

    closed: list[int] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(
            finalizer_module._manifest_boundary,
            "_acquire_parent_guard",
            lambda value: (12345, True),
        )
        scoped.setattr(
            finalizer_module,
            "_windows_handle_identity",
            lambda handle: (info.st_dev, info.st_ino + 1),
        )
        scoped.setattr(
            finalizer_module._manifest_boundary,
            "_close_windows_handle",
            lambda handle: closed.append(handle),
        )
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalizer_module._acquire_parent_guard(target)
    assert closed == [12345]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows immediate binding semantics")
@pytest.mark.parametrize("mismatch", ("parent", "path", "descriptor"))
def test_windows_immediate_binding_mismatch_precedes_first_write(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    candidate = finalizer_module._build_use_plan(
        finalizer_module._capture_use_plan_snapshot(normalized)
    )
    output = _plan_output(tmp_path, f"immediate-binding-{mismatch}.json")
    target = finalizer_module._validate_use_plan_output(output, paths=normalized)
    original_write = finalizer_module.os.write
    writes: list[bytes] = []

    def observe_write(descriptor: int, data: bytes) -> int:
        writes.append(data)
        return original_write(descriptor, data)

    with monkeypatch.context() as scoped:
        scoped.setattr(finalizer_module.os, "write", observe_write)
        if mismatch == "parent":
            original_identity = finalizer_module._windows_handle_identity
            identity_calls = 0

            def drift_parent(handle: int) -> tuple[int, int]:
                nonlocal identity_calls
                identity_calls += 1
                observed = original_identity(handle)
                if identity_calls == 2:
                    return (observed[0], observed[1] + 1)
                return observed

            scoped.setattr(finalizer_module, "_windows_handle_identity", drift_parent)
        elif mismatch == "path":
            original_revalidate = finalizer_module._revalidate_output_target
            revalidations = 0

            def drift_path(
                observed_target: object,
                *,
                must_be_absent: bool,
            ) -> None:
                nonlocal revalidations
                revalidations += 1
                if revalidations == 3:
                    raise TrustedLocalUsePlanFinalizationError("synthetic pathname parent mismatch")
                original_revalidate(
                    observed_target,
                    must_be_absent=must_be_absent,
                )

            scoped.setattr(finalizer_module, "_revalidate_output_target", drift_path)
        else:
            original_open = finalizer_module._open_exclusive_artifact
            original_fstat = finalizer_module.os.fstat
            output_descriptors: set[int] = set()
            identity_drifted = False

            def capture_descriptor(*args: object, **kwargs: object) -> int:
                descriptor = original_open(*args, **kwargs)
                output_descriptors.add(descriptor)
                return descriptor

            def drift_descriptor(descriptor: int) -> os.stat_result:
                nonlocal identity_drifted
                observed = original_fstat(descriptor)
                if descriptor in output_descriptors and not identity_drifted:
                    identity_drifted = True
                    values = list(observed)
                    values[1] = observed.st_ino + 1
                    return os.stat_result(values)
                return observed

            scoped.setattr(
                finalizer_module,
                "_open_exclusive_artifact",
                capture_descriptor,
            )
            scoped.setattr(finalizer_module.os, "fstat", drift_descriptor)
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalizer_module._create_new_artifact(
                target,
                candidate,
                parser=parse_real_asset_use_plan_v1_json,
                maximum_bytes=finalizer_module._PLAN_MAX_BYTES,
                field="Use Plan",
            )
    assert writes == []
    _assert_ordinary_rollback_result(output)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows effective-token semantics")
def test_windows_effective_token_priority_fallback_and_checked_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeFunction:
        def __init__(self, callback: object) -> None:
            self.callback = callback
            self.argtypes: object = None
            self.restype: object = None

        def __call__(self, *args: object) -> object:
            return self.callback(*args)

    high_thread = 0x1234_5678_8765_4321
    high_process = 0x2234_5678_8765_4321
    high_token = 0x3234_5678_8765_4321
    process_calls: list[int] = []
    thread_inputs: list[int] = []

    def open_thread(
        thread: int,
        access: int,
        open_as_self: bool,
        token_pointer: object,
    ) -> bool:
        assert access == 0x0008
        assert open_as_self is True
        thread_inputs.append(thread)
        token_pointer._obj.value = high_token
        return True

    def open_process(*args: object) -> bool:
        del args
        process_calls.append(1)
        return False

    advapi32 = SimpleNamespace(
        OpenThreadToken=FakeFunction(open_thread),
        OpenProcessToken=FakeFunction(open_process),
    )
    kernel32 = SimpleNamespace(
        GetCurrentThread=FakeFunction(lambda: high_thread),
        GetCurrentProcess=FakeFunction(lambda: high_process),
    )
    token = finalizer_module._open_windows_effective_token(advapi32, kernel32)
    assert token.value == high_token
    assert thread_inputs == [high_thread]
    assert process_calls == []

    last_error = [1008]
    monkeypatch.setattr(
        finalizer_module._windows_ctypes,
        "get_last_error",
        lambda: last_error[0],
    )
    fallback_calls: list[int] = []

    def no_thread_token(*args: object) -> bool:
        del args
        last_error[0] = 1008
        return False

    def process_token(
        process: int,
        access: int,
        token_pointer: object,
    ) -> bool:
        assert access == 0x0008
        fallback_calls.append(process)
        token_pointer._obj.value = high_token
        return True

    fallback_advapi32 = SimpleNamespace(
        OpenThreadToken=FakeFunction(no_thread_token),
        OpenProcessToken=FakeFunction(process_token),
    )
    fallback_kernel32 = SimpleNamespace(
        GetCurrentThread=FakeFunction(lambda: high_thread),
        GetCurrentProcess=FakeFunction(lambda: high_process),
    )
    fallback = finalizer_module._open_windows_effective_token(
        fallback_advapi32,
        fallback_kernel32,
    )
    assert fallback.value == high_token
    assert fallback_calls == [high_process]

    denied_process_calls: list[int] = []

    def denied_thread(*args: object) -> bool:
        del args
        last_error[0] = 5
        return False

    denied_advapi32 = SimpleNamespace(
        OpenThreadToken=FakeFunction(denied_thread),
        OpenProcessToken=FakeFunction(lambda *args: denied_process_calls.append(1)),
    )
    with pytest.raises(OSError):
        finalizer_module._open_windows_effective_token(
            denied_advapi32,
            fallback_kernel32,
        )
    assert denied_process_calls == []

    closed: list[int] = []

    def close_handle(handle: object) -> bool:
        closed.append(handle.value)
        return True

    cleanup_kernel32 = SimpleNamespace(CloseHandle=FakeFunction(close_handle))
    finalizer_module._close_windows_checked_handle(cleanup_kernel32, fallback)
    assert closed == [high_token]
    cleanup_kernel32.CloseHandle = FakeFunction(lambda handle: False)
    last_error[0] = 6
    with pytest.raises(OSError):
        finalizer_module._close_windows_checked_handle(cleanup_kernel32, fallback)

    freed: list[int] = []

    def local_free(pointer: object) -> None:
        freed.append(pointer.value)
        return None

    cleanup_kernel32.LocalFree = FakeFunction(local_free)
    pointer = finalizer_module._windows_wintypes.LPVOID(high_token)
    finalizer_module._windows_local_free(cleanup_kernel32, pointer)
    assert freed == [high_token]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows GenericMap semantics")
def test_windows_ace_masks_are_compared_after_file_generic_mapping() -> None:
    assert (
        finalizer_module._normalized_file_access_mask(finalizer_module._FILE_ALL_ACCESS)
        == finalizer_module._FILE_ALL_ACCESS
    )
    assert (
        finalizer_module._normalized_file_access_mask(finalizer_module._GENERIC_ALL)
        == finalizer_module._FILE_ALL_ACCESS
    )
    assert (
        finalizer_module._normalized_file_access_mask(finalizer_module._GENERIC_READ)
        == finalizer_module._FILE_GENERIC_READ
    )
    assert (
        finalizer_module._normalized_file_access_mask(finalizer_module._GENERIC_ALL | 0x01000000)
        != finalizer_module._FILE_ALL_ACCESS
    )


def test_plan_filename_suffix_and_outcome_tokens_fail_closed(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)
    for name in (
        "plan.txt",
        "plan-pass.json",
        "plan-needs-revision.json",
        "plan-rejected.json",
        "plan-approved.json",
        "plan-authorized.json",
    ):
        output = _plan_output(tmp_path, name)
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalize_use_plan(
                use_plan_closure.paths,
                output,
                expected_plan_id=readiness.plan_id,
                expected_plan_sha256=readiness.plan_sha256,
            )
        assert not output.exists()

    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    accepted = _plan_output(tmp_path, "mixed-case-use-plan.JSON")
    assert (
        finalizer_module._validate_use_plan_output(
            accepted,
            paths=normalized,
        ).path
        == accepted
    )
    for name in (
        "PaSs.json",
        "paſs.json",
        "NEEDS-REVISION.json",
        "REJECTED.json",
        "APPROVED.json",
        "AUTHORIZED.json",
    ):
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalizer_module._validate_use_plan_output(
                _plan_output(tmp_path, name),
                paths=normalized,
            )

    for token in ("LATEST", "lateſt", "current", "NeWeSt"):
        mutable_parent = (tmp_path / token).resolve()
        mutable_parent.mkdir()
        with pytest.raises(TrustedLocalUsePlanFinalizationError):
            finalizer_module._validate_use_plan_output(
                mutable_parent / "use-plan.json",
                paths=normalized,
            )
    ads_like = Path(f"{_plan_output(tmp_path, 'ads-use-plan.json')}:private")
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalizer_module._validate_use_plan_output(ads_like, paths=normalized)


def test_cli_success_serialization_and_exact_command_specific_members(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    common = _cli_args(use_plan_closure.paths)
    assert main(["inspect-use-plan-ready", *common]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n") and not captured.out.endswith("\n\n")
    inspected = json.loads(captured.out)
    assert inspected == {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "operation": "inspect-use-plan-ready",
        "plan_id": inspected["plan_id"],
        "plan_sha256": inspected["plan_sha256"],
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "status": "READY_FOR_USE_PLAN_FINALIZATION",
    }
    assert captured.out == (
        json.dumps(
            inspected,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )

    output = _plan_output(tmp_path)
    assert (
        main(
            [
                "finalize-use-plan",
                *common,
                "--expected-plan-id",
                inspected["plan_id"],
                "--expected-plan-sha256",
                inspected["plan_sha256"],
                "--output",
                str(output),
            ]
        )
        == 0
    )
    finalized_capture = capsys.readouterr()
    assert finalized_capture.err == ""
    finalized = json.loads(finalized_capture.out)
    assert finalized == {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "operation": "finalize-use-plan",
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "status": "USE_PLAN_FINALIZED",
    }
    assert finalized_capture.out == (
        json.dumps(finalized, separators=(",", ":"), sort_keys=True) + "\n"
    )

    assert main(["verify-use-plan", *common, "--use-plan-file", str(output)]) == 0
    verified_capture = capsys.readouterr()
    assert verified_capture.err == ""
    verified = json.loads(verified_capture.out)
    assert verified == {
        "current_gate": "HUMAN_GATE",
        "execution_authorized": False,
        "operation": "verify-use-plan",
        "posts_allowed": 0,
        "provider_requests": 0,
        "provider_state": "NOT_AUTHORIZED",
        "status": "USE_PLAN_HISTORICALLY_VERIFIED",
    }
    assert verified_capture.out == (
        json.dumps(verified, separators=(",", ":"), sort_keys=True) + "\n"
    )


def test_cli_malformed_anchor_is_rejected_before_paths_are_materialized(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("argument parsing must reject the guard first")

    monkeypatch.setattr(finalizer_module, "_paths_from_namespace", forbidden)
    result = main(
        [
            "finalize-use-plan",
            *_cli_args(use_plan_closure.paths),
            "--expected-plan-id",
            "invalid",
            "--expected-plan-sha256",
            "0" * 64,
            "--output",
            str(_plan_output(tmp_path)),
        ]
    )
    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert captured.err == '{"error":"FAILED_CLOSED"}\n'

    common = _cli_args(use_plan_closure.paths)
    rejected_argv = (
        ["--help"],
        ["inspect-use-plan-ready", *common, "--force"],
        ["inspect-use-plan-ready", *common, "--pack-roo", common[1]],
        ["inspect-use-plan-ready", *common, "--evidence", common[33]],
        [
            "finalize-use-plan",
            *common,
            "--expected-plan-id",
            "real_asset_use_plan_v1_00000000000000000000",
            "--expected-plan-id",
            "real_asset_use_plan_v1_11111111111111111111",
            "--expected-plan-sha256",
            "0" * 64,
            "--output",
            str(_plan_output(tmp_path)),
        ],
    )
    for argv in rejected_argv:
        assert main(argv) == 2
        rejected = capsys.readouterr()
        assert rejected.out == ""
        assert rejected.err == '{"error":"FAILED_CLOSED"}\n'


def test_cli_quarantine_result_is_bounded_and_distinct(
    use_plan_closure: SyntheticUsePlanClosure,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness = inspect_use_plan_ready(use_plan_closure.paths)

    def quarantine(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise TrustedLocalUsePlanQuarantineRequired("private detail")

    monkeypatch.setattr(finalizer_module, "finalize_use_plan", quarantine)
    result = main(
        [
            "finalize-use-plan",
            *_cli_args(use_plan_closure.paths),
            "--expected-plan-id",
            readiness.plan_id,
            "--expected-plan-sha256",
            readiness.plan_sha256,
            "--output",
            str(_plan_output(tmp_path)),
        ]
    )
    captured = capsys.readouterr()
    assert result == 3
    assert captured.out == ""
    assert captured.err == '{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}\n'
    assert "private detail" not in captured.err


def test_public_surface_and_ast_prohibit_clock_network_discovery_and_authority() -> None:
    assert finalizer_module.__all__ == [
        "TrustedLocalUsePlanPaths",
        "UsePlanReadinessV27",
        "TrustedLocalUsePlanFinalizationError",
        "TrustedLocalUsePlanQuarantineRequired",
        "inspect_use_plan_ready",
        "finalize_use_plan",
        "verify_use_plan",
        "main",
    ]
    assert issubclass(
        TrustedLocalUsePlanQuarantineRequired,
        TrustedLocalUsePlanFinalizationError,
    )
    assert TrustedLocalUsePlanPaths.__dataclass_params__.frozen is True
    assert UsePlanReadinessV27.__dataclass_params__.frozen is True
    assert TrustedLocalUsePlanPaths.__slots__ == ("manifest_sources", "rights_manifest")
    assert UsePlanReadinessV27.__slots__ == ("status", "plan_id", "plan_sha256")
    assert list(get_type_hints(TrustedLocalUsePlanPaths)) == [
        "manifest_sources",
        "rights_manifest",
    ]
    assert list(get_type_hints(UsePlanReadinessV27)) == [
        "status",
        "plan_id",
        "plan_sha256",
    ]
    assert str(inspect.signature(inspect_use_plan_ready)) == (
        "(paths: 'TrustedLocalUsePlanPaths') -> 'UsePlanReadinessV27'"
    )
    assert str(inspect.signature(finalize_use_plan)) == (
        "(paths: 'TrustedLocalUsePlanPaths', output_path: 'Path', *, "
        "expected_plan_id: 'str', expected_plan_sha256: 'str') -> "
        "'CreativeSampleRealAssetUsePlanV1'"
    )
    assert str(inspect.signature(verify_use_plan)) == (
        "(paths: 'TrustedLocalUsePlanPaths', use_plan_path: 'Path') -> "
        "'CreativeSampleRealAssetUsePlanV1'"
    )
    assert str(inspect.signature(main)) == "(argv: 'list[str] | None' = None) -> 'int'"
    source = inspect.getsource(finalizer_module)
    tree = ast.parse(source)
    for token in (
        ".glob(",
        ".rglob(",
        "os.walk(",
        "os.scandir(",
        "datetime.now(",
        "datetime.utcnow(",
        "requests.",
        "httpx.",
        "observed_at",
    ):
        assert token not in source
    assert source.count("manifest_at=None") == 1
    forbidden_import_fragments = {
        "authorization",
        "entitlement",
        "ledger",
        "migration",
        "provider",
        "runtime",
        "temporal",
        "worker",
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
        "inspect-use-plan-ready",
        "finalize-use-plan",
        "verify-use-plan",
    }


def test_snapshot_equality_detects_file_seal_link_or_time_drift(
    use_plan_closure: SyntheticUsePlanClosure,
) -> None:
    normalized = finalizer_module._normalize_use_plan_paths(use_plan_closure.paths)
    snapshot = finalizer_module._capture_use_plan_snapshot(normalized)
    first = snapshot.manifest_snapshot.files[0]
    drifted_first = replace(first, identity=(*first.identity[:3], first.identity[3] + 1))
    drifted_manifest = replace(
        snapshot.manifest_snapshot,
        files=(drifted_first, *snapshot.manifest_snapshot.files[1:]),
    )
    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalizer_module._assert_use_plan_snapshot_unchanged(
            snapshot,
            replace(snapshot, manifest_snapshot=drifted_manifest),
        )


@pytest.mark.parametrize("phase", ("opened", "after"))
def test_link_count_is_revalidated_on_opened_handle_and_after_read_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    source_path = (tmp_path / "single-link-source.bin").resolve()
    source_path.write_bytes(b"synthetic-only")
    source = finalizer_module._read_safe(
        source_path,
        max_bytes=1024,
        field="synthetic source",
    )
    seal = finalizer_module._file_seal(source)

    def changed_link_count(value: os.stat_result) -> SimpleNamespace:
        return SimpleNamespace(
            st_mode=value.st_mode,
            st_dev=value.st_dev,
            st_ino=value.st_ino,
            st_size=value.st_size,
            st_mtime_ns=value.st_mtime_ns,
            st_nlink=2,
            st_file_attributes=getattr(value, "st_file_attributes", 0),
        )

    if phase == "opened":
        original_fstat = os.fstat
        monkeypatch.setattr(
            finalizer_module.os,
            "fstat",
            lambda descriptor: changed_link_count(original_fstat(descriptor)),
        )
    else:
        original_lstat = Path.lstat
        calls = 0

        def lstat(path: Path) -> os.stat_result | SimpleNamespace:
            nonlocal calls
            calls += 1
            observed = original_lstat(path)
            return changed_link_count(observed) if calls == 2 else observed

        monkeypatch.setattr(Path, "lstat", lstat)

    with pytest.raises(TrustedLocalUsePlanFinalizationError):
        finalizer_module._revalidate_file_link_counts((seal,))
