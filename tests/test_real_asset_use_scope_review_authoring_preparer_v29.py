from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import stat
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

import sdc.real_asset_closure_path_checklist_v28 as checklist_v28
import sdc.real_asset_use_scope_review_authoring_preparer_v29 as authoring_module
import sdc.real_asset_use_scope_review_finalizer_v27 as review_finalizer

_DOCUMENT_TYPE = "sdc.trusted-local-use-scope-review-authoring-draft"
_DRAFT_FORMAT_VERSION = "1.0.0"
_TARGET_MODULE = "sdc.real_asset_use_scope_review_finalizer_v27"
_TARGET_VERSION = "v2.7"
_INSPECT_STATUS = "AUTHORING_CANDIDATE_INSPECTED_FOR_SEPARATE_CREATE_APPROVAL_ONLY"
_FINALIZE_STATUS = "AUTHORING_INPUT_CREATED_FOR_SEPARATE_MANUAL_V27_PREFLIGHT_ONLY"
_USAGE_RESTRICTION = "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"
_GATES = (
    "COPYRIGHT_USE_SCOPE",
    "LIKENESS_USE_SCOPE",
    "PRIVACY_USE_SCOPE",
    "TERRITORY_USE_SCOPE",
    "CONTENT_ROLE_USE_SCOPE",
    "OFFLINE_ONLY_RESTRICTIONS",
)
_COMMON_SUMMARY = {
    "automated_execution_allowed": False,
    "current_gate": "HUMAN_GATE",
    "execution_authorized": False,
    "manual_confirmation_required": True,
    "posts_allowed": 0,
    "preparer_version": "v2.9",
    "provider_requests": 0,
    "provider_state": "NOT_AUTHORIZED",
    "target_finalizer_module": _TARGET_MODULE,
    "target_finalizer_version": _TARGET_VERSION,
    "usage_restriction": _USAGE_RESTRICTION,
}


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _compact(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _maker_payload(
    text: str = "合成测试：请求对既定离线用途范围进行人工复核。",
) -> dict[str, object]:
    return {"request_basis": text}


def _checker_payload(
    *,
    disposition: str = "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY",
    failed_gate: int | None = None,
) -> dict[str, object]:
    gates: list[dict[str, object]] = [
        {"approved": True, "gate": gate, "note": None} for gate in _GATES
    ]
    if failed_gate is not None:
        gates[failed_gate] = {
            "approved": False,
            "gate": _GATES[failed_gate],
            "note": "合成测试：该项仍需修订。",
        }
    return {
        "checker_basis": "合成测试：逐项核对六项用途范围。",
        "disposition": disposition,
        "gate_results": gates,
    }


def _draft_envelope(role: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "authoring_role": role,
        "document_type": _DOCUMENT_TYPE,
        "draft_format_version": _DRAFT_FORMAT_VERSION,
        "payload": payload,
        "target_finalizer_module": _TARGET_MODULE,
        "target_finalizer_version": _TARGET_VERSION,
    }


def _set_synthetic_effective_owner(path: Path) -> None:
    if os.name != "nt":
        return

    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    convert_sid = advapi32.ConvertStringSidToSidW
    convert_sid.argtypes = (wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPVOID))
    convert_sid.restype = wintypes.BOOL
    set_owner = advapi32.SetNamedSecurityInfoW
    set_owner.argtypes = (
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )
    set_owner.restype = wintypes.DWORD
    local_free = kernel32.LocalFree
    local_free.argtypes = (wintypes.HLOCAL,)
    local_free.restype = wintypes.HLOCAL

    expected_sid = review_finalizer._plan_boundary._windows_effective_user_sid_string()
    sid = wintypes.LPVOID()
    assert convert_sid(expected_sid, ctypes.byref(sid))
    try:
        assert set_owner(str(path), 1, 1, sid, None, None, None) == 0
    finally:
        assert not local_free(sid)
    assert authoring_module._windows_named_owner_sid(path) == expected_sid


def _write_draft(
    tmp_path: Path,
    role: str,
    payload: dict[str, object],
    *,
    ordinal: int = 0,
    raw: bytes | None = None,
) -> Path:
    draft_parent = (tmp_path / f"draft-area-{ordinal:03d}").resolve()
    draft_parent.mkdir()
    _set_synthetic_effective_owner(draft_parent)
    draft = draft_parent / f"synthetic.{role.casefold()}-authoring-draft-v29.json"
    draft.write_bytes(raw if raw is not None else _canonical(_draft_envelope(role, payload)))
    _set_synthetic_effective_owner(draft)
    return draft


def _output_parent(tmp_path: Path, *, ordinal: int = 0) -> Path:
    parent = (tmp_path / f"authoring-output-area-{ordinal:03d}").resolve()
    parent.mkdir()
    _set_synthetic_effective_owner(parent)
    return parent


def _render_parent(path: Path) -> str:
    rendered = str(path)
    if os.name == "nt":
        rendered = rendered.replace("/", "\\")
        anchor = str(Path(path.anchor)).replace("/", "\\")
        return rendered if rendered == anchor else rendered.rstrip("\\")
    return rendered if rendered == path.anchor else rendered.rstrip("/")


def _independent_parent_seal(parent: Path) -> str:
    info = parent.stat()
    payload = {
        "normalized_absolute_path": _render_parent(parent),
        "physical_identity": [info.st_dev, info.st_ino],
        "platform": "WINDOWS" if os.name == "nt" else "POSIX",
        "st_file_attributes": int(getattr(info, "st_file_attributes", 0)),
        "st_gid": info.st_gid,
        "st_mode": info.st_mode,
        "st_uid": info.st_uid,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(b"sdc:v29:output-parent-seal\0" + raw).hexdigest()


def _assert_common_summary(payload: dict[str, object]) -> None:
    for key, value in _COMMON_SUMMARY.items():
        assert payload[key] == value


def _invoke(
    argv: list[str],
    capfdbinary: pytest.CaptureFixture[bytes],
) -> tuple[int, bytes, bytes]:
    code = authoring_module.main(argv)
    captured = capfdbinary.readouterr()
    return code, captured.out, captured.err


def _inspect(
    *,
    role: str,
    draft: Path,
    output_parent: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> dict[str, object]:
    command = f"inspect-{role.casefold()}-authoring"
    code, stdout, stderr = _invoke(
        [command, "--draft", str(draft), "--output-parent", str(output_parent)],
        capfdbinary,
    )
    assert code == 0
    assert stderr == b""
    payload = json.loads(stdout)
    assert stdout == _compact(payload)
    assert payload["operation"] == command
    assert payload["status"] == _INSPECT_STATUS
    assert payload["authoring_role"] == role
    _assert_common_summary(payload)
    return payload


def _finalize(
    *,
    role: str,
    draft: Path,
    output: Path,
    inspected: dict[str, object],
    capfdbinary: pytest.CaptureFixture[bytes],
) -> dict[str, object]:
    command = f"finalize-{role.casefold()}-authoring"
    code, stdout, stderr = _invoke(
        [
            command,
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            str(inspected["candidate_authoring_sha256"]),
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert code == 0
    assert stderr == b""
    payload = json.loads(stdout)
    assert stdout == _compact(payload)
    assert payload["operation"] == command
    assert payload["status"] == _FINALIZE_STATUS
    assert payload["authoring_role"] == role
    _assert_common_summary(payload)
    return payload


def test_public_surface_and_role_specific_signatures_are_exact_and_frozen() -> None:
    assert authoring_module.__all__ == [
        "AuthoringInspectionV29",
        "PreparedAuthoringInputV29",
        "TrustedLocalReviewAuthoringPreparationError",
        "TrustedLocalReviewAuthoringQuarantineRequired",
        "finalize_checker_authoring",
        "finalize_maker_authoring",
        "inspect_checker_authoring",
        "inspect_maker_authoring",
        "main",
    ]
    assert str(inspect.signature(authoring_module.inspect_maker_authoring)) == (
        "(draft_path: 'Path', output_parent: 'Path') -> 'AuthoringInspectionV29'"
    )
    assert inspect.signature(authoring_module.inspect_checker_authoring) == inspect.signature(
        authoring_module.inspect_maker_authoring
    )
    expected_finalize = (
        "(draft_path: 'Path', output_path: 'Path', *, expected_draft_sha256: 'str', "
        "expected_authoring_sha256: 'str', expected_output_parent_seal_sha256: 'str') "
        "-> 'PreparedAuthoringInputV29'"
    )
    assert str(inspect.signature(authoring_module.finalize_maker_authoring)) == expected_finalize
    assert inspect.signature(authoring_module.finalize_checker_authoring) == inspect.signature(
        authoring_module.finalize_maker_authoring
    )
    assert str(inspect.signature(authoring_module.main)) == (
        "(argv: 'list[str] | None' = None) -> 'int'"
    )
    inspected = authoring_module.AuthoringInspectionV29(
        status=_INSPECT_STATUS,
        authoring_role="MAKER",
        draft_sha256="1" * 64,
        candidate_authoring_sha256="2" * 64,
        candidate_authoring_size_bytes=1,
        required_output_filename=(
            "maker_use_scope_review_authoring_input_v27_22222222222222222222.json"
        ),
        output_parent_seal_sha256="3" * 64,
    )
    with pytest.raises(FrozenInstanceError):
        inspected.authoring_role = "CHECKER"  # type: ignore[misc]
    assert issubclass(
        authoring_module.TrustedLocalReviewAuthoringQuarantineRequired,
        authoring_module.TrustedLocalReviewAuthoringPreparationError,
    )
    with pytest.raises(authoring_module.TrustedLocalReviewAuthoringPreparationError):
        authoring_module.inspect_maker_authoring("not-a-path", Path("not-a-path"))  # type: ignore[arg-type]


def test_bound_v27_and_v28_public_surfaces_remain_exact() -> None:
    assert review_finalizer.__all__ == [
        "TrustedLocalUsePlanArtifactPaths",
        "TrustedLocalUseScopeReviewRequestPaths",
        "TrustedLocalUseScopeReviewInstructionPaths",
        "TrustedLocalUseScopeReviewVerificationPaths",
        "UseScopeReviewRequestPreflightV27",
        "UseScopeReviewInstructionPreflightV27",
        "TrustedLocalUseScopeReviewFinalizationError",
        "TrustedLocalUseScopeReviewQuarantineRequired",
        "preflight_review_request",
        "preflight_review_instruction",
        "finalize_review_record",
        "verify_review_record",
        "main",
    ]
    assert checklist_v28.__all__ == [
        "ClosurePathChecklistEntryV28",
        "TrustedLocalClosurePathChecklistError",
        "TrustedLocalClosurePathChecklistV28",
        "build_closure_path_checklist_v28",
        "main",
    ]


@pytest.mark.parametrize(
    ("role", "payload", "prefix"),
    (
        ("MAKER", _maker_payload(), "maker_use_scope_review_authoring_input_v27_"),
        ("CHECKER", _checker_payload(), "checker_use_scope_review_authoring_input_v27_"),
    ),
)
def test_inspect_and_finalize_create_exact_v27_authoring_input(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    role: str,
    payload: dict[str, object],
    prefix: str,
) -> None:
    draft = _write_draft(tmp_path, role, payload)
    parent = _output_parent(tmp_path)
    before = draft.read_bytes()
    inspected = _inspect(
        role=role,
        draft=draft,
        output_parent=parent,
        capfdbinary=capfdbinary,
    )

    expected = _canonical(payload)
    expected_sha256 = hashlib.sha256(expected).hexdigest()
    expected_name = f"{prefix}{expected_sha256[:20]}.json"
    assert set(inspected) == {
        *_COMMON_SUMMARY,
        "authoring_role",
        "candidate_authoring_sha256",
        "candidate_authoring_size_bytes",
        "draft_sha256",
        "operation",
        "output_parent_seal_sha256",
        "required_output_filename",
        "status",
    }
    assert inspected["draft_sha256"] == hashlib.sha256(before).hexdigest()
    assert inspected["candidate_authoring_sha256"] == expected_sha256
    assert inspected["candidate_authoring_size_bytes"] == len(expected)
    assert inspected["required_output_filename"] == expected_name
    assert isinstance(inspected["output_parent_seal_sha256"], str)
    assert len(str(inspected["output_parent_seal_sha256"])) == 64
    assert list(parent.iterdir()) == []
    assert draft.read_bytes() == before

    output = parent / expected_name
    finalized = _finalize(
        role=role,
        draft=draft,
        output=output,
        inspected=inspected,
        capfdbinary=capfdbinary,
    )
    assert set(finalized) == {
        *_COMMON_SUMMARY,
        "authoring_input_sha256",
        "authoring_input_size_bytes",
        "authoring_role",
        "draft_sha256",
        "operation",
        "status",
    }
    assert finalized["draft_sha256"] == inspected["draft_sha256"]
    assert finalized["authoring_input_sha256"] == expected_sha256
    assert finalized["authoring_input_size_bytes"] == len(expected)
    assert output.read_bytes() == expected
    assert draft.read_bytes() == before
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
    descriptor = os.open(output, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        review_finalizer._plan_boundary._assert_owner_only_descriptor(descriptor)
    finally:
        os.close(descriptor)
    if role == "MAKER":
        parsed, _ = review_finalizer._read_maker_authoring(output)
        assert parsed.request_basis == payload["request_basis"]
    else:
        parsed, _ = review_finalizer._read_checker_authoring(output)
        assert parsed.checker_basis == payload["checker_basis"]
        assert parsed.disposition == payload["disposition"]


def test_transport_format_changes_raw_draft_hash_not_candidate_hash(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    envelope = _draft_envelope("MAKER", _maker_payload())
    canonical = _canonical(envelope)
    reordered_crlf = (
        (json.dumps(envelope, ensure_ascii=False, indent=4, sort_keys=False) + "\r\n")
        .replace("\n", "\r\n")
        .replace("\r\r\n", "\r\n")
        .encode()
    )
    first = _write_draft(tmp_path, "MAKER", _maker_payload(), ordinal=1, raw=canonical)
    second = _write_draft(tmp_path, "MAKER", _maker_payload(), ordinal=2, raw=reordered_crlf)
    first_result = _inspect(
        role="MAKER",
        draft=first,
        output_parent=_output_parent(tmp_path, ordinal=1),
        capfdbinary=capfdbinary,
    )
    second_result = _inspect(
        role="MAKER",
        draft=second,
        output_parent=_output_parent(tmp_path, ordinal=2),
        capfdbinary=capfdbinary,
    )
    assert first_result["draft_sha256"] != second_result["draft_sha256"]
    assert first_result["candidate_authoring_sha256"] == second_result["candidate_authoring_sha256"]
    assert first_result["required_output_filename"] == second_result["required_output_filename"]


def test_output_parent_seal_has_the_exact_documented_domain_and_ignores_mtime(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    first = _inspect(
        role="MAKER",
        draft=draft,
        output_parent=parent,
        capfdbinary=capfdbinary,
    )
    assert first["output_parent_seal_sha256"] == _independent_parent_seal(parent)
    before = parent.stat().st_mtime_ns
    os.utime(parent, ns=(parent.stat().st_atime_ns, before + 1_000_000))
    second = _inspect(
        role="MAKER",
        draft=draft,
        output_parent=parent,
        capfdbinary=capfdbinary,
    )
    assert second["output_parent_seal_sha256"] == first["output_parent_seal_sha256"]


@pytest.mark.skipif(os.name != "nt", reason="Windows submitted-case semantics")
def test_output_parent_seal_preserves_submitted_windows_case(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    submitted = parent.with_name(parent.name.upper())
    assert submitted.exists()
    original = _inspect(
        role="MAKER",
        draft=draft,
        output_parent=parent,
        capfdbinary=capfdbinary,
    )
    varied = _inspect(
        role="MAKER",
        draft=draft,
        output_parent=submitted,
        capfdbinary=capfdbinary,
    )
    assert varied["output_parent_seal_sha256"] == _independent_parent_seal(submitted)
    assert varied["output_parent_seal_sha256"] != original["output_parent_seal_sha256"]


def test_parent_capture_rejects_mixed_physical_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _output_parent(tmp_path)
    real_identity = authoring_module._manifest_boundary._directory_identity

    def mismatched_identity(path: Path, *, field: str) -> tuple[int, int, int, int]:
        observed = real_identity(path, field=field)
        return (observed[0], observed[1] + 1, observed[2], observed[3])

    monkeypatch.setattr(
        authoring_module._manifest_boundary,
        "_directory_identity",
        mismatched_identity,
    )
    with pytest.raises(authoring_module.TrustedLocalReviewAuthoringPreparationError):
        authoring_module._capture_parent(parent)


def test_inspect_requires_the_digest_derived_target_to_be_absent(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    payload = _maker_payload()
    draft = _write_draft(tmp_path, "MAKER", payload)
    parent = _output_parent(tmp_path)
    digest = hashlib.sha256(_canonical(payload)).hexdigest()
    output = parent / f"maker_use_scope_review_authoring_input_v27_{digest[:20]}.json"
    sentinel = b"synthetic independent winner"
    output.write_bytes(sentinel)

    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
        ],
        capfdbinary,
    )

    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert output.read_bytes() == sentinel


def test_role_specific_complete_suffix_is_case_insensitive_but_not_interchangeable(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload(), ordinal=1)
    uppercase = draft.with_name("SYNTHETIC.MAKER-AUTHORING-DRAFT-V29.JSON")
    draft.rename(uppercase)
    accepted = _inspect(
        role="MAKER",
        draft=uppercase,
        output_parent=_output_parent(tmp_path, ordinal=1),
        capfdbinary=capfdbinary,
    )
    assert accepted["authoring_role"] == "MAKER"

    mismatched = _write_draft(tmp_path, "MAKER", _maker_payload(), ordinal=2)
    checker_suffix = mismatched.with_name("synthetic.checker-authoring-draft-v29.json")
    mismatched.rename(checker_suffix)
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(checker_suffix),
            "--output-parent",
            str(_output_parent(tmp_path, ordinal=2)),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_role_command_suffix_envelope_and_payload_are_four_separate_guards(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    envelope_role_mismatch = _write_draft(
        tmp_path,
        "CHECKER",
        _checker_payload(),
        ordinal=1,
        raw=_canonical(_draft_envelope("MAKER", _maker_payload())),
    )
    maker_payload_under_checker_role = _write_draft(
        tmp_path,
        "CHECKER",
        _maker_payload(),
        ordinal=2,
        raw=_canonical(_draft_envelope("CHECKER", _maker_payload())),
    )
    for ordinal, draft in enumerate(
        (envelope_role_mismatch, maker_payload_under_checker_role),
        start=1,
    ):
        code, stdout, stderr = _invoke(
            [
                "inspect-checker-authoring",
                "--draft",
                str(draft),
                "--output-parent",
                str(_output_parent(tmp_path, ordinal=ordinal + 10)),
            ],
            capfdbinary,
        )
        assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_oversize_draft_fails_closed_at_the_raw_transport_boundary(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(
        tmp_path,
        "MAKER",
        _maker_payload(),
        raw=b"{" + (b" " * 65_536),
    )
    parent = _output_parent(tmp_path)
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert list(parent.iterdir()) == []


def test_relative_draft_and_shared_draft_output_parent_fail_closed(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    separate_parent = _output_parent(tmp_path)
    relative_draft = Path(os.path.relpath(draft, Path.cwd()))
    invocations = (
        [
            "inspect-maker-authoring",
            "--draft",
            str(relative_draft),
            "--output-parent",
            str(separate_parent),
        ],
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(draft.parent),
        ],
    )
    for argv in invocations:
        code, stdout, stderr = _invoke(argv, capfdbinary)
        assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_repository_and_mutable_alias_drafts_fail_before_read(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _output_parent(tmp_path)
    monkeypatch.setitem(authoring_module._DRAFT_SUFFIXES, "MAKER", ".py")
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(Path(__file__).resolve()),
            "--output-parent",
            str(parent),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')

    monkeypatch.setitem(
        authoring_module._DRAFT_SUFFIXES,
        "MAKER",
        ".maker-authoring-draft-v29.json",
    )
    alias_parent = tmp_path / "current"
    alias_parent.mkdir()
    alias = alias_parent / "synthetic.maker-authoring-draft-v29.json"
    alias.write_bytes(_canonical(_draft_envelope("MAKER", _maker_payload())))
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(alias.resolve()),
            "--output-parent",
            str(parent),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


@pytest.mark.parametrize(
    ("mutation", "role"),
    (
        (lambda value: {**value, "unknown": False}, "MAKER"),
        (lambda value: {key: item for key, item in value.items() if key != "payload"}, "MAKER"),
        (lambda value: {**value, "document_type": "wrong"}, "MAKER"),
        (lambda value: {**value, "draft_format_version": "2.0.0"}, "MAKER"),
        (lambda value: {**value, "target_finalizer_module": "sdc.wrong"}, "MAKER"),
        (lambda value: {**value, "target_finalizer_version": "v2.8"}, "MAKER"),
        (lambda value: {**value, "authoring_role": "CHECKER"}, "MAKER"),
        (lambda value: {**value, "payload": None}, "MAKER"),
    ),
)
def test_draft_envelope_is_exact_and_role_bound(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    mutation: Any,
    role: str,
) -> None:
    envelope = mutation(_draft_envelope(role, _maker_payload()))
    draft = _write_draft(tmp_path, role, _maker_payload(), raw=_canonical(envelope))
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(_output_parent(tmp_path)),
        ],
        capfdbinary,
    )
    assert code == 2
    assert stdout == b""
    assert stderr == b'{"error":"FAILED_CLOSED"}\n'


@pytest.mark.parametrize(
    "raw",
    (
        b"",
        b"\xef\xbb\xbf{}\n",
        b"\xff\n",
        b'{"authoring_role":"MAKER","authoring_role":"MAKER"}\n',
        b'{"authoring_role":NaN}\n',
        b"[]\n",
    ),
)
def test_malformed_transport_fails_closed_without_output(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    raw: bytes,
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload(), raw=raw)
    parent = _output_parent(tmp_path)
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize(
    "text",
    (
        "",
        " leading",
        "trailing ",
        "e\u0301",
        "line\nbreak",
        "delete\x7f",
        "x" * 2001,
    ),
)
def test_maker_human_text_boundary_matches_v27(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    text: str,
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload(text))
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(_output_parent(tmp_path)),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: {**value, "disposition": "PASS_FOR_PROVIDER_PROPOSAL_DESIGN_ONLY"},
        lambda value: {**value, "disposition": "UNKNOWN"},
        lambda value: {**value, "gate_results": value["gate_results"][:-1]},
        lambda value: {
            **value,
            "gate_results": [
                value["gate_results"][1],
                value["gate_results"][0],
                *value["gate_results"][2:],
            ],
        },
        lambda value: {
            **value,
            "gate_results": [
                {**value["gate_results"][0], "approved": 1},
                *value["gate_results"][1:],
            ],
        },
        lambda value: {
            **value,
            "gate_results": [
                value["gate_results"][0],
                {**value["gate_results"][1], "note": "unexpected"},
                *value["gate_results"][2:],
            ],
        },
    ),
)
def test_checker_gate_order_types_notes_and_disposition_are_exact(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    mutate: Any,
) -> None:
    base = _checker_payload(disposition="NEEDS_REVISION", failed_gate=0)
    draft = _write_draft(tmp_path, "CHECKER", mutate(base))
    code, stdout, stderr = _invoke(
        [
            "inspect-checker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(_output_parent(tmp_path)),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


@pytest.mark.parametrize("disposition", ("NEEDS_REVISION", "REJECTED"))
def test_checker_negative_dispositions_require_and_accept_a_failed_gate(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    disposition: str,
) -> None:
    draft = _write_draft(
        tmp_path,
        "CHECKER",
        _checker_payload(disposition=disposition, failed_gate=0),
    )
    result = _inspect(
        role="CHECKER",
        draft=draft,
        output_parent=_output_parent(tmp_path),
        capfdbinary=capfdbinary,
    )
    assert (
        result["candidate_authoring_sha256"]
        == hashlib.sha256(
            _canonical(_checker_payload(disposition=disposition, failed_gate=0))
        ).hexdigest()
    )


@pytest.mark.parametrize(
    "guard",
    ("draft_sha256", "candidate_authoring_sha256", "output_parent_seal_sha256"),
)
def test_finalize_requires_all_three_exact_inspected_hash_guards(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    guard: str,
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(role="MAKER", draft=draft, output_parent=parent, capfdbinary=capfdbinary)
    output = parent / str(inspected["required_output_filename"])
    values = {
        "draft_sha256": str(inspected["draft_sha256"]),
        "candidate_authoring_sha256": str(inspected["candidate_authoring_sha256"]),
        "output_parent_seal_sha256": str(inspected["output_parent_seal_sha256"]),
    }
    values[guard] = "0" * 64
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            values["draft_sha256"],
            "--expected-authoring-sha256",
            values["candidate_authoring_sha256"],
            "--expected-output-parent-seal-sha256",
            values["output_parent_seal_sha256"],
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert not output.exists()


def test_malformed_expected_hash_fails_before_private_draft_capture(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = False

    def unexpected_capture(path: Path, *, role: object) -> object:
        del path, role
        nonlocal captured
        captured = True
        raise AssertionError("draft capture must not start")

    monkeypatch.setattr(authoring_module, "_capture_draft", unexpected_capture)
    output = _output_parent(tmp_path) / (
        "maker_use_scope_review_authoring_input_v27_00000000000000000000.json"
    )
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(tmp_path / "absent.maker-authoring-draft-v29.json"),
            "--output",
            str(output),
            "--expected-draft-sha256",
            "A" * 64,
            "--expected-authoring-sha256",
            "0" * 64,
            "--expected-output-parent-seal-sha256",
            "0" * 64,
        ],
        capfdbinary,
    )
    assert not captured
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_full_candidate_hash_not_only_filename_prefix_is_the_finalize_guard(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(role="MAKER", draft=draft, output_parent=parent, capfdbinary=capfdbinary)
    actual = str(inspected["candidate_authoring_sha256"])
    replacement = "0" if actual[20] != "0" else "1"
    same_prefix_wrong_full_hash = actual[:20] + replacement + actual[21:]
    output = parent / str(inspected["required_output_filename"])
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            same_prefix_wrong_full_hash,
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert same_prefix_wrong_full_hash[:20] == actual[:20]
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert not output.exists()


def test_finalize_rejects_any_output_basename_other_than_hash_bound_name(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(role="MAKER", draft=draft, output_parent=parent, capfdbinary=capfdbinary)
    output = parent / "maker-authoring-input.json"
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            str(inspected["candidate_authoring_sha256"]),
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert not output.exists()


def test_create_new_never_overwrites_existing_output(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(role="MAKER", draft=draft, output_parent=parent, capfdbinary=capfdbinary)
    output = parent / str(inspected["required_output_filename"])
    sentinel = b"synthetic pre-existing bytes"
    output.write_bytes(sentinel)
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            str(inspected["candidate_authoring_sha256"]),
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
    assert output.read_bytes() == sentinel


def test_draft_need_not_be_owner_only_but_is_never_modified(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    if os.name != "nt":
        draft.chmod(0o644)
    before = (draft.read_bytes(), draft.stat().st_mode)
    _inspect(
        role="MAKER",
        draft=draft,
        output_parent=_output_parent(tmp_path),
        capfdbinary=capfdbinary,
    )
    assert (draft.read_bytes(), draft.stat().st_mode) == before


def test_hard_linked_draft_is_rejected(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    alias = draft.with_name("draft-alias.json")
    os.link(draft, alias)
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(_output_parent(tmp_path)),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_symbolic_linked_draft_is_rejected_where_supported(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    alias = draft.with_name("draft-link.json")
    try:
        alias.symlink_to(draft)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    code, stdout, stderr = _invoke(
        [
            "inspect-maker-authoring",
            "--draft",
            str(alias),
            "--output-parent",
            str(_output_parent(tmp_path)),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')


def test_finalize_rolls_back_the_exact_new_output_after_write_failure(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(role="MAKER", draft=draft, output_parent=parent, capfdbinary=capfdbinary)
    output = parent / str(inspected["required_output_filename"])
    real_fsync = os.fsync
    injected = False

    def fail_once(descriptor: int) -> None:
        nonlocal injected
        if not injected:
            injected = True
            raise OSError("synthetic output fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(authoring_module.os, "fsync", fail_once)
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            str(inspected["candidate_authoring_sha256"]),
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert injected
    assert code in {2, 3}
    assert stdout == b""
    assert stderr in {
        b'{"error":"FAILED_CLOSED"}\n',
        b'{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}\n',
    }
    if output.exists():
        assert output.read_bytes() != _canonical(_maker_payload())


def test_unconfirmed_explicit_rollback_is_always_quarantine(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    inspected = _inspect(
        role="MAKER",
        draft=draft,
        output_parent=parent,
        capfdbinary=capfdbinary,
    )
    output = parent / str(inspected["required_output_filename"])

    class SyntheticCreated:
        closed = False

    def synthetic_create(*args: object, **kwargs: object) -> SyntheticCreated:
        del args, kwargs
        return SyntheticCreated()

    def synthetic_commit_failure(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise review_finalizer._plan_boundary.TrustedLocalUsePlanFinalizationError(
            "synthetic commit failure"
        )

    def synthetic_rollback_failure(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OSError("synthetic rollback failure")

    monkeypatch.setattr(authoring_module._plan_boundary, "_create_new_artifact", synthetic_create)
    monkeypatch.setattr(
        authoring_module._plan_boundary,
        "_commit_created_artifact",
        synthetic_commit_failure,
    )
    monkeypatch.setattr(
        authoring_module._plan_boundary,
        "_rollback_created_artifact",
        synthetic_rollback_failure,
    )
    code, stdout, stderr = _invoke(
        [
            "finalize-maker-authoring",
            "--draft",
            str(draft),
            "--output",
            str(output),
            "--expected-draft-sha256",
            str(inspected["draft_sha256"]),
            "--expected-authoring-sha256",
            str(inspected["candidate_authoring_sha256"]),
            "--expected-output-parent-seal-sha256",
            str(inspected["output_parent_seal_sha256"]),
        ],
        capfdbinary,
    )
    assert (code, stdout, stderr) == (
        3,
        b"",
        b'{"error":"ROLLBACK_UNCONFIRMED_QUARANTINE_REQUIRED"}\n',
    )
    assert not output.exists()


def test_cli_rejects_aliases_duplicates_and_authority_adjacent_options(
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    draft = _write_draft(tmp_path, "MAKER", _maker_payload())
    parent = _output_parent(tmp_path)
    rejected = (
        ["--help"],
        ["inspect-maker", "--draft", str(draft), "--output-parent", str(parent)],
        ["inspect-maker-authoring", "--dra", str(draft), "--output-parent", str(parent)],
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
        ],
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
            "--requested-at",
            "2026-08-22T00:00:00Z",
        ],
        [
            "inspect-maker-authoring",
            "--draft",
            str(draft),
            "--output-parent",
            str(parent),
            "--force",
        ],
    )
    for argv in rejected:
        code, stdout, stderr = _invoke(argv, capfdbinary)
        assert (code, stdout, stderr) == (2, b"", b'{"error":"FAILED_CLOSED"}\n')
        assert str(tmp_path).encode() not in stderr


def test_no_finalizer_checklist_clock_network_or_discovery_surface() -> None:
    source = inspect.getsource(authoring_module)
    tree = ast.parse(source)
    forbidden_calls = (
        ".glob(",
        ".rglob(",
        ".iterdir(",
        "glob.glob(",
        "glob.iglob(",
        "os.listdir(",
        "os.scandir(",
        "os.walk(",
        ".mkdir(",
        ".write_text(",
        ".write_bytes(",
        "datetime.now(",
        "datetime.utcnow(",
        "time.time(",
        "subprocess.",
        "preflight_review_request(",
        "preflight_review_instruction(",
        "finalize_review_record(",
        "verify_review_record(",
        "build_closure_path_checklist_v28(",
    )
    for token in forbidden_calls:
        assert token not in source
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
        "inspect-maker-authoring",
        "inspect-checker-authoring",
        "finalize-maker-authoring",
        "finalize-checker-authoring",
    }
    forbidden_import_fragments = {
        "authorization",
        "entitlement",
        "ledger",
        "provider",
        "requests",
        "runtime",
        "socket",
        "subprocess",
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
