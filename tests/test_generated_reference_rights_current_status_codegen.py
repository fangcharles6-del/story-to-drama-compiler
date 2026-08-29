from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
from typing import cast

import pytest

import sdc.generated_reference_rights_current_status_codegen as codegen
from sdc.schemas import MODELS

ROOT = Path(__file__).parents[1]


def _raw(path: str) -> bytes:
    return (ROOT / path).read_bytes()


def _materialize_protected_tree(root: Path) -> None:
    for relative_path in codegen._PROTECTED_FINGERPRINTS:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_raw(relative_path))


def test_reviewed_source_and_upstream_inputs_have_exact_frozen_bytes() -> None:
    assert codegen._PROTECTED_FINGERPRINTS == {
        codegen._REVIEWED_SOURCE_PATH: (
            46_739,
            "d6c74ecb90c4c14abe47dbbd3d4ecd8fff8d5a4e0e90dbb2edae166773160315",
        ),
        codegen._CANDIDATE_SOURCE_PATH: (
            101_487,
            "b385164d9dabd467308250da41166e1a0d47b8cf8504eb15b5644590aa9edb55",
        ),
        codegen._CANDIDATE_GENERATED_PATH: (
            84_090,
            "aaaf5fed96b2e867a99debf9ddfcc2759febd6e87ccb7defef3e4ae5f0b120a3",
        ),
        codegen._CHARACTER_PNG_PATH: (
            5_841,
            "3c20c94c18fbd72b68a58748bae9aba2daefc6baa38e9fc1c6ab30b40e6f39fc",
        ),
    }
    for relative_path, (size, digest) in codegen._PROTECTED_FINGERPRINTS.items():
        raw = _raw(relative_path)
        assert len(raw) == size
        assert hashlib.sha256(raw).hexdigest() == digest


def test_reviewed_source_exact_shape_and_zero_authority_scope_are_frozen() -> None:
    raw = _raw(codegen._REVIEWED_SOURCE_PATH)
    value = codegen._parse_canonical_document(raw, label="reviewed source fixture")
    case = codegen._assert_source_shape(value)
    positive_cases = cast(list[object], value["positive_cases"])
    historical_cases = cast(list[object], value["historical_qualification_expiry_cases"])
    qualification = cast(dict[str, object], case["qualification"])
    manifest = cast(dict[str, object], case["manifest"])
    current_status = cast(dict[str, object], case["current_status"])
    assert case["case_id"] == "character-reference-current-v1"
    assert len(positive_cases) == 1
    assert len(historical_cases) == 2
    assert len(cast(list[object], qualification["expected_gate_results"])) == 15
    assert len(cast(list[object], qualification["refreshed_evidence_reviews"])) == 10
    assert len(cast(list[object], manifest["review_evidence_documents"])) == 9
    assert len(cast(list[object], manifest["human_gate_reviews"])) == 9
    assert len(cast(list[object], current_status["observations"])) == 9


def test_complete_typed_raw_known_answer_closure_is_deterministic() -> None:
    first = codegen._build_expected_closure(ROOT)
    second = codegen._build_expected_closure(ROOT)
    assert first.derived_raw == second.derived_raw
    assert first.derived_value == second.derived_value
    assert 1 <= len(first.derived_raw) <= codegen._MAX_DERIVED_BYTES
    assert first.derived_value["known_answer_version"] == "1.0.0"
    assert first.derived_value["manifest_policy_document_sha256"] == (
        "7d9f72f134b5be5f68bb55f25ee898736bd84d39b2ff6917e0e2ecab447f8f16"
    )
    assert first.derived_value["current_status_policy_document_sha256"] == (
        "cf596012ca0d3bf88d1e49d0aea11184428d047d0e919822032da51f792d61e0"
    )
    historical = cast(
        list[dict[str, object]],
        first.derived_value["historical_qualification_expiry_cases"],
    )
    assert len(historical) == 2
    assert all(item["manifest_created"] is False for item in historical)
    assert all(
        item["observed_failure_code"] == "TIME_WINDOW_INVALID_OR_EXPIRED"
        for item in historical
    )
    case = cast(list[dict[str, object]], first.derived_value["positive_cases"])[0]
    decision = cast(dict[str, object], case["current_status_decision"])
    assessment = cast(dict[str, object], case["record_as_of_assessment"])
    receipt = cast(dict[str, object], case["record_as_of_assessment_receipt"])
    assert case["case_id"] == "character-reference-current-v1"
    assert len(cast(list[object], case["source_observations"])) == 9
    assert len(cast(list[object], case["explicit_chain_inputs"])) == 9
    assert decision["recorded_status"] == "CURRENT"
    assert assessment["as_of_status"] == "CURRENT"
    assert receipt["as_of_status"] == "CURRENT"


def test_checked_in_derived_fixture_matches_complete_rebuild() -> None:
    expected = codegen._build_expected_closure(ROOT)
    actual = _raw(codegen._DERIVED_FIXTURE_PATH)
    assert actual == expected.derived_raw
    assert codegen._parse_canonical_document(
        actual,
        label="derived known-answer fixture",
    ) == expected.derived_value


def test_persistent_parser_rejects_noncanonical_and_resource_limit_values() -> None:
    canonical = codegen._canonical_document_bytes({"a": 1})
    assert codegen._parse_canonical_document(canonical, label="fixture") == {"a": 1}
    for raw in (
        b'{"a":1}\n',
        b'{"a": 1}\r\n',
        b'\xef\xbb\xbf{"a": 1}\n',
        b'{"a": 1, "a": 2}\n',
        b'{"a": NaN}\n',
    ):
        with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
            codegen._parse_canonical_document(raw, label="fixture")
    nested: object = "leaf"
    for _ in range(codegen._MAX_JSON_CONTAINER_DEPTH + 1):
        nested = [nested]
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._canonical_document_bytes(nested)
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._canonical_document_bytes(list(range(codegen._MAX_JSON_CONTAINER_ITEMS + 1)))
    deeply_nested_raw = b'{"a":' + (b"[" * 2_000) + b"0" + (b"]" * 2_000) + b"}\n"
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._parse_canonical_document(deeply_nested_raw, label="fixture")


def test_read_frozen_rejects_source_drift(tmp_path: Path) -> None:
    _materialize_protected_tree(tmp_path)
    source = tmp_path / codegen._REVIEWED_SOURCE_PATH
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(
        codegen.GeneratedReferenceRightsCurrentStatusCodegenError,
        match="frozen exact bytes",
    ):
        codegen._read_frozen(
            tmp_path,
            codegen._REVIEWED_SOURCE_PATH,
            max_bytes=codegen._MAX_SOURCE_BYTES,
            label="reviewed source fixture",
        )


def test_stable_reader_rejects_symlink_and_hardlink(tmp_path: Path) -> None:
    ordinary = tmp_path / "ordinary.json"
    ordinary.write_bytes(b"{}\n")
    hardlink = tmp_path / "hardlink.json"
    try:
        os.link(ordinary, hardlink)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._read_stable_regular_file(ordinary, max_bytes=100, label="fixture")
    symlink = tmp_path / "symlink.json"
    try:
        symlink.symlink_to(hardlink)
    except OSError:
        return
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._read_stable_regular_file(symlink, max_bytes=100, label="fixture")


def test_fixture_path_rejects_escape_and_symlinked_ancestor(tmp_path: Path) -> None:
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._safe_path(tmp_path, "../outside.json", label="fixture")
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this host")
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._safe_path(tmp_path, "linked/value.json", label="fixture")


def test_writer_directly_writes_only_fixed_derived_target(tmp_path: Path) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    raw = codegen._canonical_document_bytes({"known_answer_version": "test"})
    codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, raw)
    assert derived.read_bytes() == raw
    with pytest.raises(
        codegen.GeneratedReferenceRightsCurrentStatusCodegenError,
        match="single fixed derived-fixture allowlist",
    ):
        codegen._write_exact_derived(tmp_path, codegen._REVIEWED_SOURCE_PATH, raw)
    for relative_path in codegen._PROTECTED_FINGERPRINTS:
        assert (tmp_path / relative_path).read_bytes() == _raw(relative_path)


def test_writer_rejects_hardlinked_destination(tmp_path: Path) -> None:
    _materialize_protected_tree(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.parent.mkdir(parents=True, exist_ok=True)
    peer = tmp_path / "peer.json"
    peer.write_bytes(b"{}\n")
    try:
        os.link(peer, derived)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(codegen.GeneratedReferenceRightsCurrentStatusCodegenError):
        codegen._write_exact_derived(
            tmp_path,
            codegen._DERIVED_FIXTURE_PATH,
            codegen._canonical_document_bytes({"value": 1}),
        )


def test_check_mode_has_no_reachable_write_path(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(
        codegen,
        "_build_expected_closure",
        lambda root: sentinel,
    )
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


def test_cli_has_only_explicit_fixed_root_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(codegen, "_repository_root", lambda: ROOT)
    monkeypatch.setattr(codegen, "_build_expected_closure", lambda root: sentinel)
    monkeypatch.setattr(codegen, "_check_closure", lambda root, closure: None)
    monkeypatch.setattr(codegen, "_update_closure", lambda root, closure: None)
    assert codegen.main(["--check"]) == 0
    assert codegen.main(["--update"]) == 0
    for argv in ([], ["--check", "--update"], ["--root", str(ROOT)], ["--unknown"]):
        with pytest.raises(SystemExit):
            codegen.main(argv)


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
    write_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            isinstance(nested, ast.Call)
            and (
                (
                    isinstance(nested.func, ast.Attribute)
                    and nested.func.attr
                    in {"ftruncate", "write", "write_bytes", "write_text"}
                )
                or (isinstance(nested.func, ast.Name) and nested.func.id == "open")
            )
            for nested in ast.walk(node)
        )
    ]
    assert [item.name for item in write_functions] == ["_write_exact_derived"]


def test_old_fourteen_fixtures_and_seventy_six_schemas_are_outside_update_allowlist() -> None:
    old_fixture_paths = set(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests/fixtures/visual_prompt_profiles").rglob("*")
        if path.is_file() and "generated-reference-rights-current-status" not in path.as_posix()
    )
    assert len(old_fixture_paths) == 14
    assert set(codegen._PROTECTED_FINGERPRINTS) <= old_fixture_paths | {
        codegen._REVIEWED_SOURCE_PATH
    }
    assert codegen._DERIVED_FIXTURE_PATH not in old_fixture_paths
    schema_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "schemas").glob("*.schema.json")
    }
    old_schema_paths = {f"schemas/{model.__name__}.schema.json" for model in MODELS[:76]}
    assert len(MODELS) == 83
    assert len(schema_paths) == 83
    assert len(old_schema_paths) == 76
    assert old_schema_paths <= schema_paths
    assert codegen._DERIVED_FIXTURE_PATH not in old_schema_paths
