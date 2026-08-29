from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import stat
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from sdc import generated_reference_candidate_codegen as codegen
from sdc.generated_reference_candidate import EVIDENCE_CATEGORY_ORDER

ROOT = Path(__file__).parents[1]
SOURCE_PATH = ROOT / codegen._REVIEWED_SOURCE_PATH
DERIVED_PATH = ROOT / codegen._DERIVED_FIXTURE_PATH
PNG_PATHS = tuple(ROOT / value for value in codegen._PNG_FINGERPRINTS)
CASE_IDS = (
    "character-reference-pass",
    "scene-reference-pass",
)
FALSE_AUTHORITY_FIELDS = (
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
)
ZERO_AUTHORITY_FIELDS = (
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
)


@pytest.fixture(scope="module")
def closure() -> codegen._ExpectedClosure:
    return codegen._build_expected_closure(ROOT)


def _canonical_document(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _source_value() -> dict[str, object]:
    value = json.loads(SOURCE_PATH.read_bytes())
    assert type(value) is dict
    return cast(dict[str, object], value)


def _copy_protected_inputs(root: Path) -> None:
    destination_directory = root / codegen._FIXTURE_DIRECTORY
    destination_directory.mkdir(parents=True)
    for relative_path in (codegen._REVIEWED_SOURCE_PATH, *codegen._PNG_FINGERPRINTS):
        source = ROOT / relative_path
        destination = root / relative_path
        destination.write_bytes(source.read_bytes())


def _tree_snapshot(root: Path) -> dict[str, tuple[bytes, int, int]]:
    result: dict[str, tuple[bytes, int, int]] = {}
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            info = path.stat()
            result[path.relative_to(root).as_posix()] = (
                path.read_bytes(),
                info.st_size,
                info.st_mtime_ns,
            )
    return result


def _assert_zero_authority(value: dict[str, object]) -> None:
    for field in FALSE_AUTHORITY_FIELDS:
        assert value[field] is False
    for field in ZERO_AUTHORITY_FIELDS:
        assert type(value[field]) is int and value[field] == 0
    assert value["authority_scope"] == (
        "THIS_DOCUMENT_GRANTS_NO_PROVIDER_RUNTIME_OR_ASSET_USE_AUTHORITY"
    )
    assert value["current_gate"] == "HUMAN_GATE"
    assert value["provider_state"] == "NOT_AUTHORIZED"
    assert value["usage_restriction"] == "MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION"


def test_reviewed_source_has_exact_frozen_bytes_and_document_codec() -> None:
    raw = SOURCE_PATH.read_bytes()
    value = _source_value()

    assert len(raw) == codegen._REVIEWED_SOURCE_SIZE_BYTES
    assert hashlib.sha256(raw).hexdigest() == codegen._REVIEWED_SOURCE_RAW_SHA256
    assert raw == _canonical_document(value)
    assert codegen._parse_canonical_document(raw, label="reviewed source") == value
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8")
    assert unicodedata.normalize("NFC", text) == text


def test_reviewed_source_exact_shape_order_and_synthetic_scope_are_frozen() -> None:
    value = _source_value()
    cases = cast(list[dict[str, object]], value["cases"])

    assert tuple(value) == codegen._SOURCE_ROOT_KEYS
    assert value["known_answer_version"] == "1.0.0"
    assert [case["case_id"] for case in cases] == list(CASE_IDS)
    assert all(tuple(case) == codegen._SOURCE_CASE_KEYS for case in cases)
    for case in cases:
        case_id = cast(str, case["case_id"])
        review = cast(dict[str, object], case["synthetic_review"])
        assert review == codegen._SYNTHETIC_REVIEW_VALUES[case_id]
        assert review["provider_used"] is False
        assert review["external_material_used"] is False
        assert case["png_path"] == codegen._CASE_PNG_PATHS[case_id]

    source_folded = SOURCE_PATH.read_text(encoding="utf-8").casefold()
    for external_marker in (
        "http://",
        "https://",
        "openai",
        "midjourney",
        "disney",
        "marvel",
        "credential",
        "api_key",
    ):
        assert external_marker not in source_folded


@pytest.mark.parametrize(
    ("field", "substitute"),
    [
        ("external_material_used", 0),
        ("provider_used", 0),
    ],
)
def test_reviewed_source_rejects_boolean_integer_pseudo_equality(
    field: str,
    substitute: int,
) -> None:
    value = _source_value()
    cases = cast(list[dict[str, object]], value["cases"])
    review = cast(dict[str, object], cases[0]["synthetic_review"])
    review[field] = substitute
    with pytest.raises(
        codegen.GeneratedReferenceCandidateCodegenError,
        match="synthetic-media declaration values",
    ):
        codegen._validate_source_document(value)


def test_synthetic_pngs_have_exact_frozen_bytes_and_plain_rgb_shape() -> None:
    for relative_path, (expected_size, expected_sha) in codegen._PNG_FINGERPRINTS.items():
        raw = (ROOT / relative_path).read_bytes()
        assert len(raw) == expected_size
        assert hashlib.sha256(raw).hexdigest() == expected_sha
        assert raw.startswith(b"\x89PNG\r\n\x1a\n")
        assert raw[12:16] == b"IHDR"
        assert int.from_bytes(raw[16:20], "big") == 512
        assert int.from_bytes(raw[20:24], "big") == 512
        assert raw[24:29] == bytes((8, 2, 0, 0, 0))
        assert b"acTL" not in raw and b"fcTL" not in raw and b"fdAT" not in raw


def test_expected_derived_closure_is_deterministic_complete_and_zero_authority(
    closure: codegen._ExpectedClosure,
) -> None:
    repeated = codegen._build_expected_closure(ROOT)
    document = closure.derived_value
    cases = cast(list[dict[str, object]], document["cases"])

    assert repeated.protected == closure.protected
    assert repeated.derived_raw == closure.derived_raw
    assert repeated.derived_value == document
    assert document["known_answer_version"] == "1.0.0"
    assert [case["case_id"] for case in cases] == list(CASE_IDS)
    assert all(tuple(case) == codegen._DERIVED_CASE_KEYS for case in cases)
    assert closure.derived_raw == _canonical_document(document)
    assert b"\r" not in closure.derived_raw
    assert len(closure.derived_raw) <= codegen._MAX_DERIVED_BYTES

    source_cases = cast(list[dict[str, object]], closure.protected.source_value["cases"])
    for source_case, derived_case in zip(source_cases, cases, strict=True):
        artifact = cast(dict[str, object], derived_case["artifact"])
        outcome = cast(dict[str, object], derived_case["provider_attempt_outcome"])
        candidate = cast(dict[str, object], derived_case["candidate"])
        request = cast(dict[str, object], derived_case["qualification_request"])
        decision = cast(dict[str, object], derived_case["qualification_decision"])

        assert artifact == source_case["artifact"]
        assert outcome["terminal_disposition"] == "VERIFIED_SUCCESS"
        assert outcome["verified_output_count"] == 1
        assert len(cast(list[object], outcome["output_descriptors"])) == 1
        assert candidate["candidate_state"] == "CAPTURED_UNQUALIFIED"
        assert candidate["qualification_decision_embedded"] is False
        assert request["status"] == "QUALIFICATION_REQUESTED"
        assert len(cast(list[object], request["evidence_refs"])) == 10
        assert decision["status"] == "QUALIFICATION_COMPLETE"
        assert decision["qualification_performed"] is True
        assert decision["decision"] == "PASS_FOR_SEPARATE_GENERATED_RIGHTS_MANIFEST_REVIEW"
        assert decision["eligible_for_separate_generated_rights_manifest_review"] is True
        assert decision["qualification_issue_codes"] == []
        decision_gates = cast(list[dict[str, object]], decision["gate_results"])
        assert [item["result"] for item in decision_gates] == ["PASS"] * 15
        for formal_document in (outcome, candidate, request, decision):
            _assert_zero_authority(formal_document)


def test_reviewed_evidence_and_human_records_close_exact_bytes() -> None:
    cases = cast(list[dict[str, object]], _source_value()["cases"])
    for case in cases:
        evidence = cast(list[dict[str, object]], case["evidence_documents"])
        evidence_categories = [
            cast(dict[str, object], item["reference"])["category"] for item in evidence
        ]
        assert evidence_categories == list(EVIDENCE_CATEGORY_ORDER)
        evidence_digests: list[str] = []
        for item in evidence:
            document_bytes = _canonical_document(item["document"])
            reference = cast(dict[str, object], item["reference"])
            assert reference["document_size_bytes"] == len(document_bytes)
            assert reference["document_sha256"] == hashlib.sha256(document_bytes).hexdigest()
            evidence_digests.append(reference["document_sha256"])
        assert len(set(evidence_digests)) == 10

        retained_values = (
            case["preparer_reference"],
            case["preparer_action"],
            case["qualifier_reference"],
            case["qualifier_action"],
        )
        retained_digests = [
            hashlib.sha256(_canonical_document(item)).hexdigest() for item in retained_values
        ]
        assert len(set(retained_digests)) == 4
        assert set(retained_digests).isdisjoint(evidence_digests)
        assert case["preparer_reference"] != case["qualifier_reference"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda raw: b"\xef\xbb\xbf" + raw, "no-BOM"),
        (lambda raw: raw.replace(b"\n", b"\r\n"), "LF-only"),
        (lambda raw: raw[:-1], "exactly one LF"),
        (
            lambda raw: raw.replace(
                b'{\n  "cases":',
                b'{\n  "cases": [],\n  "cases":',
                1,
            ),
            "duplicate object key",
        ),
        (
            lambda raw: raw.replace(b"fictional", "fictio\u0301nal".encode(), 1),
            "NFC",
        ),
    ],
)
def test_persistent_parser_fails_closed_for_noncanonical_bytes(
    mutation: Callable[[bytes], bytes],
    message: str,
) -> None:
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match=message):
        codegen._parse_canonical_document(mutation(SOURCE_PATH.read_bytes()), label="mutated")


def test_persistent_json_container_boundaries_are_exact() -> None:
    value: object = "leaf"
    for _ in range(codegen._MAX_JSON_CONTAINER_DEPTH):
        value = [value]
    codegen._validate_json_value(value)
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="container-depth"):
        codegen._validate_json_value([value])

    codegen._validate_json_value([None] * codegen._MAX_JSON_CONTAINER_ITEMS)
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="item boundary"):
        codegen._validate_json_value([None] * (codegen._MAX_JSON_CONTAINER_ITEMS + 1))


def test_check_mode_is_byte_and_timestamp_read_only(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_protected_inputs(tmp_path)
    (tmp_path / codegen._DERIVED_FIXTURE_PATH).write_bytes(closure.derived_raw)
    (tmp_path / "unrelated.keep").write_bytes(b"preserve\n")
    before = _tree_snapshot(tmp_path)
    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(
        codegen,
        "_write_exact_derived",
        lambda *_args, **_kwargs: pytest.fail("--check reached a write path"),
    )

    assert codegen.main(["--check"]) == 0
    assert codegen.main(["--check"]) == 0
    assert _tree_snapshot(tmp_path) == before


@pytest.mark.parametrize("existing", [False, True])
def test_update_directly_writes_only_the_fixed_derived_fixture(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    _copy_protected_inputs(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    if existing:
        derived.write_bytes(b"stale\n")
    unrelated = tmp_path / "unrelated.keep"
    unrelated.write_bytes(b"preserve\n")
    protected_before = {
        path: (tmp_path / path).read_bytes()
        for path in (codegen._REVIEWED_SOURCE_PATH, *codegen._PNG_FINGERPRINTS)
    }
    real_open = os.open
    write_paths: list[Path] = []

    def recording_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            write_paths.append(Path(path).resolve())
        return real_open(path, flags, mode)

    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(os, "open", recording_open)
    monkeypatch.setattr(
        os,
        "replace",
        lambda *_args, **_kwargs: pytest.fail("update used a replacement or temporary path"),
    )

    assert codegen.main(["--update"]) == 0
    assert write_paths == [derived.resolve()]
    assert derived.read_bytes() == closure.derived_raw
    assert unrelated.read_bytes() == b"preserve\n"
    for path, raw in protected_before.items():
        assert (tmp_path / path).read_bytes() == raw
    assert set(_tree_snapshot(tmp_path)) == {
        codegen._REVIEWED_SOURCE_PATH,
        codegen._DERIVED_FIXTURE_PATH,
        *codegen._PNG_FINGERPRINTS,
        "unrelated.keep",
    }


@pytest.mark.parametrize(
    "relative_path",
    (codegen._REVIEWED_SOURCE_PATH, *codegen._PNG_FINGERPRINTS),
)
def test_update_fails_before_writing_if_any_protected_input_drifted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
) -> None:
    _copy_protected_inputs(tmp_path)
    target = tmp_path / relative_path
    raw = target.read_bytes()
    target.write_bytes(bytes((raw[0] ^ 1,)) + raw[1:])
    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(
        codegen,
        "_write_exact_derived",
        lambda *_args, **_kwargs: pytest.fail("drifted input reached a write path"),
    )

    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="SHA-256"):
        codegen.main(["--update"])
    assert not (tmp_path / codegen._DERIVED_FIXTURE_PATH).exists()


def test_update_requires_existing_fixed_parent_and_rejects_nonallowlisted_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="allowlist"):
        codegen._write_exact_derived(tmp_path, "outside.json", b"{}\n")
    with pytest.raises(
        codegen.GeneratedReferenceCandidateCodegenError,
        match="ancestor|parent directory",
    ):
        codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, b"{}\n")
    assert list(tmp_path.iterdir()) == []


def test_check_rejects_missing_and_stale_derived_fixture(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
) -> None:
    _copy_protected_inputs(tmp_path)
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError):
        codegen._check_closure(tmp_path, closure)
    (tmp_path / codegen._DERIVED_FIXTURE_PATH).write_bytes(b"{}\n")
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError):
        codegen._check_closure(tmp_path, closure)


def test_reader_rejects_symlink_reparse_point_and_hardlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(target)
    except OSError:
        alias = None  # type: ignore[assignment]
    if alias is not None:
        with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="non-symlink"):
            codegen._read_stable_regular_file(alias, max_bytes=100, label="symlink")

    fake_reparse = type(
        "FakeStat",
        (),
        {"st_mode": stat.S_IFREG, "st_file_attributes": 0x400},
    )()
    assert codegen._is_regular_non_symlink(cast(os.stat_result, fake_reparse)) is False

    hardlink = tmp_path / "hardlink.json"
    try:
        os.link(target, hardlink)
    except OSError:
        pytest.skip("this host does not permit a test hardlink")
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="one link"):
        codegen._read_stable_regular_file(target, max_bytes=100, label="hardlinked source")


def test_reader_detects_file_identity_drift_during_open_handle_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "stable.json"
    target.write_bytes(b"{}\n")
    real_identity = codegen._file_identity
    calls = 0

    def drifting_identity(info: os.stat_result) -> tuple[int, int, int, int]:
        nonlocal calls
        calls += 1
        identity = real_identity(info)
        if calls == 2:
            return identity[0], identity[1], identity[2], identity[3] + 1
        return identity

    monkeypatch.setattr(codegen, "_file_identity", drifting_identity)
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="changed"):
        codegen._read_stable_regular_file(target, max_bytes=100, label="drifting input")


def test_update_rechecks_protected_png_after_the_only_write(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_protected_inputs(tmp_path)
    png_path = tmp_path / codegen._CHARACTER_PNG_PATH

    def mutate_protected_png(
        _root: Path,
        _relative_path: str,
        _raw: bytes,
    ) -> None:
        raw = png_path.read_bytes()
        png_path.write_bytes(raw[:-1] + bytes((raw[-1] ^ 1,)))

    monkeypatch.setattr(codegen, "_write_exact_derived", mutate_protected_png)
    with pytest.raises(codegen.GeneratedReferenceCandidateCodegenError, match="SHA-256"):
        codegen._update_closure(tmp_path, closure)


def test_fixture_paths_reject_a_symlinked_ancestor(tmp_path: Path) -> None:
    real_directory = tmp_path / "real-tests"
    real_directory.mkdir()
    linked_directory = tmp_path / "tests"
    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except OSError:
        pytest.skip("this host does not permit a directory symlink")
    with pytest.raises(
        codegen.GeneratedReferenceCandidateCodegenError,
        match="ancestors.*non-symlink",
    ):
        codegen._assert_safe_fixture_path(
            tmp_path,
            codegen._REVIEWED_SOURCE_PATH,
            label="reviewed source",
        )


def test_writer_rejects_an_existing_hardlinked_destination(tmp_path: Path) -> None:
    _copy_protected_inputs(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.write_bytes(b"stale\n")
    alias = tmp_path / "derived-alias.json"
    try:
        os.link(derived, alias)
    except OSError:
        pytest.skip("this host does not permit a test hardlink")
    with pytest.raises(
        codegen.GeneratedReferenceCandidateCodegenError,
        match="one regular non-symlink file",
    ):
        codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, b"{}\n")
    assert derived.read_bytes() == b"stale\n"
    assert alias.read_bytes() == b"stale\n"


def test_cli_has_only_explicit_fixed_root_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = codegen._argument_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
    with pytest.raises(SystemExit):
        parser.parse_args(["--check", "--update"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--check", "--root", str(tmp_path)])
    assert tuple(inspect.signature(codegen._repository_root).parameters) == ()

    expected = codegen._repository_root()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDC_GENERATED_REFERENCE_CANDIDATE_ROOT", str(tmp_path))
    assert codegen._repository_root() == expected == ROOT


def test_codegen_has_one_persistence_exception_and_no_external_capability() -> None:
    source = Path(codegen.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "sdc":
                imported_modules.update(f"sdc.{alias.name}" for alias in node.names)
            else:
                imported_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                calls.add(f"{node.func.value.id}.{node.func.attr}")

    assert imported_modules <= {
        "__future__",
        "argparse",
        "dataclasses",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "pydantic",
        "sdc.generated_reference_candidate",
        "stat",
        "tomllib",
        "typing",
        "unicodedata",
    }
    assert {name for name in imported_modules if name.startswith("sdc.")} == {
        "sdc.generated_reference_candidate"
    }
    forbidden_modules = {
        "asyncpg",
        "httpx",
        "requests",
        "sdc.ark_provider",
        "sdc.canary",
        "sdc.client",
        "sdc.evidence_ledger",
        "sdc.persistence",
        "sdc.provider",
        "sdc.runtime",
        "sdc.schemas",
        "sdc.worker",
        "sdc.workflow",
        "sqlalchemy",
        "temporalio",
        "urllib",
    }
    assert all(
        imported != forbidden and not imported.startswith(f"{forbidden}.")
        for imported in imported_modules
        for forbidden in forbidden_modules
    )
    assert calls.isdisjoint(
        {
            "__import__",
            "eval",
            "exec",
            "open",
            "os.mkdir",
            "os.makedirs",
            "os.replace",
            "os.rename",
            "Path.mkdir",
        }
    )
    assert all(
        marker not in source.casefold()
        for marker in (
            "requests.",
            "urllib",
            "socket",
            "subprocess",
            "api_key",
            "os.environ",
            "getenv",
            "datetime",
            "random",
        )
    )


def test_repository_derived_fixture_is_current() -> None:
    closure = codegen._build_expected_closure(ROOT)
    assert codegen.main(["--check"]) == 0
    assert DERIVED_PATH.read_bytes() == closure.derived_raw
