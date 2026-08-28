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

from sdc import visual_reference_prompt_compiler_codegen as codegen

ROOT = Path(__file__).parents[1]
SOURCE_PATH = ROOT / codegen._REVIEWED_SOURCE_PATH
DERIVED_PATH = ROOT / codegen._DERIVED_FIXTURE_PATH
CASE_IDS = (
    "character-reference-basic",
    "character-reference-unicode-nfc",
    "scene-reference-basic-empty-props",
    "scene-reference-unicode-nfc-multi-props",
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
CHARACTER_ROLES = (
    "CHARACTER_IDENTITY_SHEET",
    "CHARACTER_POSE_REFERENCE",
    "CHARACTER_EXPRESSION_REFERENCE",
)
SCENE_ROLES = (
    "SCENE_ESTABLISHING_REFERENCE",
    "SCENE_LIGHTING_REFERENCE",
    "SCENE_MATERIAL_REFERENCE",
    "SCENE_PROP_PLACEMENT_REFERENCE",
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


def _copy_source(root: Path) -> Path:
    destination = root / codegen._REVIEWED_SOURCE_PATH
    destination.parent.mkdir(parents=True)
    destination.write_bytes(SOURCE_PATH.read_bytes())
    return destination


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
    assert value["current_gate"] == "HUMAN_GATE"
    assert value["provider_state"] == "NOT_AUTHORIZED"


def _all_object_keys(value: object) -> set[str]:
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        return set(mapping) | {
            nested_key for item in mapping.values() for nested_key in _all_object_keys(item)
        }
    if type(value) is list:
        return {
            nested_key
            for item in cast(list[object], value)
            for nested_key in _all_object_keys(item)
        }
    return set()


def test_reviewed_source_has_exact_frozen_bytes_and_document_codec() -> None:
    raw = SOURCE_PATH.read_bytes()
    value = _source_value()

    assert len(raw) == codegen._REVIEWED_SOURCE_SIZE_BYTES == 14_587
    assert hashlib.sha256(raw).hexdigest() == codegen._REVIEWED_SOURCE_RAW_SHA256
    assert raw == _canonical_document(value)
    assert codegen._parse_canonical_document(raw, label="reviewed source") == value
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8")
    assert unicodedata.normalize("NFC", text) == text


def test_reviewed_source_exact_shape_order_and_synthetic_coverage_are_frozen() -> None:
    value = _source_value()
    cases = cast(list[dict[str, object]], value["cases"])

    assert tuple(value) == ("cases", "known_answer_version")
    assert value["known_answer_version"] == "1.0.0"
    assert [case["case_id"] for case in cases] == list(CASE_IDS)
    assert all(tuple(case) == ("case_id", "request", "subject") for case in cases)
    assert all("artifact" not in case for case in cases)
    assert all(type(case["request"]) is dict for case in cases)
    assert all(type(case["subject"]) is dict for case in cases)

    requests = [cast(dict[str, object], case["request"]) for case in cases]
    assert [request["asset_purpose"] for request in requests] == [
        "CHARACTER_REFERENCE_ASSET",
        "CHARACTER_REFERENCE_ASSET",
        "SCENE_REFERENCE_ASSET",
        "SCENE_REFERENCE_ASSET",
    ]
    basic_scene = cast(dict[str, object], requests[2]["reference_source"])
    unicode_scene = cast(dict[str, object], requests[3]["reference_source"])
    assert basic_scene["props"] == []
    assert unicode_scene["props"] == ["amber-lantern", "blue-vase", "纸鹤"]
    assert unicode_scene["props"] == sorted(cast(list[str], unicode_scene["props"]))
    assert any(ord(character) > 127 for character in json.dumps(cases[1], ensure_ascii=False))
    assert any(ord(character) > 127 for character in json.dumps(cases[3], ensure_ascii=False))

    folded = SOURCE_PATH.read_text(encoding="utf-8").casefold()
    for external_marker in (
        "awesome-gpt-image-2",
        "http://",
        "https://",
        "openai",
        "midjourney",
        "disney",
        "marvel",
    ):
        assert external_marker not in folded


def test_reviewed_source_requests_bind_the_complete_bible_active_version(
    closure: codegen._ExpectedClosure,
) -> None:
    cases = cast(list[dict[str, object]], closure.source_value["cases"])

    for case in cases:
        request = cast(dict[str, object], case["request"])
        subject = cast(dict[str, object], case["subject"])
        versions = cast(list[dict[str, object]], subject["asset_versions"])
        active = [item for item in versions if item["id"] == subject["active_asset_version_id"]]
        assert len(active) == 1
        assert request["expected_active_asset_version_id"] == active[0]["id"]
        assert request["expected_active_asset_content_sha256"] == active[0]["content_sha256"]
        assert request["subject_id"] in {subject.get("character_id"), subject.get("scene_id")}
        assert active[0]["media_type"] == "image/png"
        assert active[0]["provenance"] == "IMPORTED_APPROVED_MEDIA"
        _assert_zero_authority(request)


def test_expected_derived_closure_is_deterministic_and_complete(
    closure: codegen._ExpectedClosure,
) -> None:
    repeated = codegen._build_expected_closure(ROOT)
    document = closure.derived_value
    cases = cast(list[dict[str, object]], document["cases"])

    assert repeated.source_raw == closure.source_raw
    assert repeated.derived_raw == closure.derived_raw
    assert repeated.derived_value == document
    assert document["known_answer_version"] == "1.0.0"
    assert [case["case_id"] for case in cases] == list(CASE_IDS)
    assert all(set(case) == {"case_id", "artifact"} for case in cases)
    assert closure.derived_raw == _canonical_document(document)
    assert b"\r" not in closure.derived_raw
    assert len(closure.derived_raw) <= codegen._MAX_DERIVED_BYTES

    source_cases = cast(list[dict[str, object]], closure.source_value["cases"])
    for source_case, derived_case in zip(source_cases, cases, strict=True):
        request = cast(dict[str, object], source_case["request"])
        artifact = cast(dict[str, object], derived_case["artifact"])
        snapshot = cast(dict[str, object], artifact["profile_snapshot"])
        render_input = cast(dict[str, object], artifact["render_input"])
        receipt = cast(dict[str, object], artifact["prompt_render_receipt"])

        assert artifact["reference_source"] == request["reference_source"]
        assert artifact["subject_id"] == request["subject_id"]
        assert (
            artifact["expected_active_asset_version_id"]
            == request["expected_active_asset_version_id"]
        )
        assert (
            artifact["expected_active_asset_content_sha256"]
            == request["expected_active_asset_content_sha256"]
        )
        assert artifact["selection_decision_ref"] == request["selection_decision_ref"]
        assert artifact["authoring_decision_ref"] == request["authoring_decision_ref"]
        assert snapshot["catalog_version"] == request["catalog_version"]
        assert snapshot["catalog_sha256"] == request["catalog_sha256"]
        assert snapshot["profile_id"] == request["profile_id"]
        assert snapshot["profile_version"] == request["profile_version"]
        assert snapshot["profile_sha256"] == request["profile_sha256"]
        assert artifact["render_input_sha256"] == receipt["render_input_sha256"]
        assert artifact["prompt_sha256"] == receipt["prompt_sha256"]
        assert artifact["prompt_size_bytes"] == receipt["prompt_size_bytes"]
        assert render_input["input_kind"] == request["asset_purpose"]

        prompt = cast(str, artifact["prompt"])
        prompt_bytes = prompt.encode("utf-8")
        assert unicodedata.normalize("NFC", prompt) == prompt
        assert "\r" not in prompt and prompt.endswith("\n") and not prompt.endswith("\n\n")
        assert hashlib.sha256(prompt_bytes).hexdigest() == artifact["prompt_sha256"]
        assert len(prompt_bytes) == artifact["prompt_size_bytes"]
        _assert_zero_authority(artifact)
        _assert_zero_authority(receipt)


def test_expected_derived_uses_full_roles_and_keeps_qc_and_provider_metadata_isolated(
    closure: codegen._ExpectedClosure,
) -> None:
    cases = cast(list[dict[str, object]], closure.derived_value["cases"])

    for case in cases:
        artifact = cast(dict[str, object], case["artifact"])
        snapshot = cast(dict[str, object], artifact["profile_snapshot"])
        constraint_set = cast(dict[str, object], snapshot["constraint_set"])
        roles = tuple(cast(list[str], snapshot["reference_asset_types"]))
        recipe = cast(dict[str, object], snapshot["reference_asset_recipe"])
        prompt = cast(str, artifact["prompt"])
        expected_roles = (
            CHARACTER_ROLES
            if artifact["asset_purpose"] == "CHARACTER_REFERENCE_ASSET"
            else SCENE_ROLES
        )

        assert roles == expected_roles
        assert tuple(cast(list[str], recipe["reference_asset_types"])) == expected_roles
        for expectation in cast(list[str], constraint_set["qc_expectations"]):
            assert expectation not in prompt
        keys = _all_object_keys(artifact)
        assert "provider_syntax_compatibility_observations" not in keys
        assert "provider_compatibility" not in keys
        assert "candidate" not in keys
        assert "qualification" not in keys
        assert "rights_manifest" not in keys
        assert "asset_promotion" not in keys


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
            lambda raw: raw.replace(
                b"Character Alpha",
                "Cafe\u0301 Alpha".encode(),
                1,
            ),
            "NFC",
        ),
    ],
)
def test_persistent_parser_fails_closed_for_noncanonical_bytes(
    mutation: Callable[[bytes], bytes],
    message: str,
) -> None:
    raw = mutation(SOURCE_PATH.read_bytes())
    with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError, match=message):
        codegen._parse_canonical_document(raw, label="mutated source")


def test_persistent_json_container_depth_is_exactly_sixteen() -> None:
    value: object = "leaf"
    for _ in range(16):
        value = [value]
    codegen._validate_json_value(value)

    value = [value]
    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="container-depth",
    ):
        codegen._validate_json_value(value)

    codegen._validate_json_value([None] * 64)
    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="64-item",
    ):
        codegen._validate_json_value([None] * 65)


def test_check_mode_is_byte_and_timestamp_read_only(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_source(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.write_bytes(closure.derived_raw)
    unrelated = tmp_path / "unrelated.keep"
    unrelated.write_bytes(b"preserve\n")
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
    source = _copy_source(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    if existing:
        derived.write_bytes(b"stale\n")
    unrelated = tmp_path / "unrelated.keep"
    unrelated.write_bytes(b"preserve\n")
    source_before = source.read_bytes()
    real_open = os.open
    write_paths: list[Path] = []

    def recording_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            write_paths.append(Path(path).resolve())
        return real_open(path, flags, mode)

    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(codegen.os, "open", recording_open)
    monkeypatch.setattr(
        codegen.os,
        "replace",
        lambda *_args, **_kwargs: pytest.fail("update used a replacement or temporary path"),
    )

    assert codegen.main(["--update"]) == 0
    assert write_paths == [derived.resolve()]
    assert source.read_bytes() == source_before
    assert derived.read_bytes() == closure.derived_raw
    assert unrelated.read_bytes() == b"preserve\n"
    assert set(_tree_snapshot(tmp_path)) == {
        codegen._REVIEWED_SOURCE_PATH,
        codegen._DERIVED_FIXTURE_PATH,
        "unrelated.keep",
    }


def test_update_fails_before_writing_if_source_fingerprint_drifted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _copy_source(tmp_path)
    raw = source.read_bytes()
    source.write_bytes(
        raw.replace(
            b"fixture-character-basic-authoring",
            b"fixture-character-basic-authorinh",
        )
    )
    monkeypatch.setattr(codegen, "_repository_root", lambda: tmp_path)
    monkeypatch.setattr(
        codegen,
        "_write_exact_derived",
        lambda *_args, **_kwargs: pytest.fail("drifted source reached a write path"),
    )

    with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError, match="SHA-256"):
        codegen.main(["--update"])
    assert not (tmp_path / codegen._DERIVED_FIXTURE_PATH).exists()


def test_update_requires_existing_fixed_parent_and_rejects_nonallowlisted_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="allowlist",
    ):
        codegen._write_exact_derived(tmp_path, "outside.json", b"{}\n")
    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="ancestor|parent directory",
    ):
        codegen._write_exact_derived(tmp_path, codegen._DERIVED_FIXTURE_PATH, b"{}\n")
    assert list(tmp_path.iterdir()) == []


def test_check_rejects_missing_and_stale_derived_fixture(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
) -> None:
    _copy_source(tmp_path)
    with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError):
        codegen._check_closure(tmp_path, closure)

    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.write_bytes(b"{}\n")
    with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError):
        codegen._check_closure(tmp_path, closure)


def test_reader_rejects_symlink_reparse_point_and_hardlink(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(target)
    except OSError:
        alias = None  # type: ignore[assignment]
    if alias is not None:
        with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError, match="non-symlink"):
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
    with pytest.raises(codegen.VisualReferencePromptCompilerCodegenError, match="one link"):
        codegen._read_stable_regular_file(target, max_bytes=100, label="hardlinked source")


def test_fixture_paths_reject_a_symlinked_ancestor(tmp_path: Path) -> None:
    real_directory = tmp_path / "real-tests"
    real_directory.mkdir()
    linked_directory = tmp_path / "tests"
    try:
        linked_directory.symlink_to(real_directory, target_is_directory=True)
    except OSError:
        pytest.skip("this host does not permit a directory symlink")

    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="ancestors.*non-symlink",
    ):
        codegen._assert_safe_fixture_path(
            tmp_path,
            codegen._REVIEWED_SOURCE_PATH,
            label="reviewed source",
        )


def test_writer_rejects_an_existing_hardlinked_destination(tmp_path: Path) -> None:
    _copy_source(tmp_path)
    derived = tmp_path / codegen._DERIVED_FIXTURE_PATH
    derived.write_bytes(b"stale\n")
    alias = tmp_path / "derived-alias.json"
    try:
        os.link(derived, alias)
    except OSError:
        pytest.skip("this host does not permit a test hardlink")

    with pytest.raises(
        codegen.VisualReferencePromptCompilerCodegenError,
        match="one regular non-symlink file",
    ):
        codegen._write_exact_derived(
            tmp_path,
            codegen._DERIVED_FIXTURE_PATH,
            b"{}\n",
        )
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
    monkeypatch.setenv("SDC_VISUAL_REFERENCE_PROMPT_ROOT", str(tmp_path))
    assert codegen._repository_root() == expected == ROOT


def test_codegen_has_only_the_single_persistence_exception_and_no_external_capability() -> None:
    source = Path(codegen.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                calls.add(f"{node.func.value.id}.{node.func.attr}")

    assert imported_roots <= {
        "__future__",
        "argparse",
        "dataclasses",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "pydantic",
        "sdc",
        "stat",
        "tomllib",
        "typing",
        "unicodedata",
    }
    assert "sdc.schemas" not in source
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
        )
    )


def test_repository_derived_fixture_is_current() -> None:
    closure = codegen._build_expected_closure(ROOT)
    assert codegen.main(["--check"]) == 0
    assert DERIVED_PATH.read_bytes() == closure.derived_raw
