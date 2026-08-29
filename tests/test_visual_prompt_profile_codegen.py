from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import json
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from sdc import schemas
from sdc import visual_prompt_profile_codegen as codegen
from sdc import visual_prompt_profile_source as source_module
from sdc.visual_prompt_profile_source import load_visual_prompt_profile_source
from sdc.visual_prompt_profiles import (
    VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
    VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,
    VISUAL_PROMPT_SOURCE_PATH,
    OfflineRenderAdmissionStatus,
    ProfileTextProvenanceStatus,
)

ROOT = Path(__file__).parents[1]
KNOWN_ANSWER_PATH = ROOT / VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH
CATALOG_RECEIPT_PATH = ROOT / "docs/reference/visual-prompt-catalog-digest-receipt.json"
CATALOG_RECEIPT_DOMAIN = b"sdc:visual-prompt-catalog-digest-receipt:v1\0"
RENDER_INPUT_DOMAIN = b"sdc:visual-prompt-render-input:v1\0"
PROMPT_RECEIPT_DOMAIN = b"sdc:visual-prompt-render-receipt:v1\0"


@pytest.fixture(scope="module")
def closure() -> codegen._ExpectedClosure:
    return codegen._build_expected_closure(ROOT)


def _canonical_compact(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


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


def _known_answer_value() -> dict[str, object]:
    value = json.loads(KNOWN_ANSWER_PATH.read_bytes())
    assert type(value) is dict
    return cast(dict[str, object], value)


def _receipt_value() -> dict[str, object]:
    value = json.loads(CATALOG_RECEIPT_PATH.read_bytes())
    assert type(value) is dict
    return cast(dict[str, object], value)


def _with_frozen_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> dict[str, object]:
    monkeypatch.setattr(codegen, "_KNOWN_ANSWER_RAW_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(codegen, "_KNOWN_ANSWER_SIZE_BYTES", len(raw))
    return codegen._parse_known_answer_bytes(raw)


def _file_snapshot(root: Path, paths: tuple[str, ...]) -> dict[str, tuple[bytes, int, int]]:
    snapshot: dict[str, tuple[bytes, int, int]] = {}
    for relative_path in paths:
        path = root / relative_path
        info = path.stat()
        snapshot[relative_path] = (path.read_bytes(), info.st_size, info.st_mtime_ns)
    return snapshot


def _materialize(root: Path, closure: codegen._ExpectedClosure) -> None:
    codegen._update_closure(root, closure)


def _machine_block(raw: bytes, begin: str, end: str) -> dict[str, object]:
    text = raw.decode("utf-8")
    payload = text.split(f"{begin}\n```json\n", 1)[1].split(f"```\n{end}", 1)[0]
    value = json.loads(payload)
    assert type(value) is dict
    return cast(dict[str, object], value)


def _leaf_paths(value: object, prefix: tuple[str | int, ...] = ()) -> list[tuple[str | int, ...]]:
    if type(value) is dict:
        result: list[tuple[str | int, ...]] = []
        for key, item in cast(dict[str, object], value).items():
            result.extend(_leaf_paths(item, (*prefix, key)))
        return result
    if type(value) is list:
        result = []
        for index, item in enumerate(cast(list[object], value)):
            result.extend(_leaf_paths(item, (*prefix, index)))
        return result
    return [prefix]


def _mutate_leaf(value: object, path: tuple[str | int, ...]) -> object:
    changed = json.loads(json.dumps(value, ensure_ascii=False))
    parent = changed
    for part in path[:-1]:
        parent = parent[part]  # type: ignore[index]
    leaf = path[-1]
    current = parent[leaf]  # type: ignore[index]
    if type(current) is bool:
        replacement: object = not current
    elif type(current) is int:
        replacement = current + 1
    else:
        assert type(current) is str
        replacement = f"{current}.changed"
    parent[leaf] = replacement  # type: ignore[index]
    return changed


def test_reviewed_known_answer_has_exact_frozen_bytes_and_strict_admission() -> None:
    raw = KNOWN_ANSWER_PATH.read_bytes()

    assert len(raw) == codegen._KNOWN_ANSWER_SIZE_BYTES == 17_678
    assert hashlib.sha256(raw).hexdigest() == codegen._KNOWN_ANSWER_RAW_SHA256
    assert codegen._parse_known_answer_bytes(raw) == _known_answer_value()
    assert raw == _canonical_document(_known_answer_value())
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda raw: raw.replace(b"\n", b"\r\n"), "LF only"),
        (lambda raw: raw[:-1], "persistent canonical JSON"),
        (
            lambda raw: raw.replace(
                b'{\n  "cases":',
                b'{\n  "cases": [],\n  "cases":',
                1,
            ),
            "duplicate key",
        ),
        (lambda raw: raw.replace(b'"ordinal": 10', b'"ordinal": 10.0', 1), "floating-point"),
        (lambda raw: raw.replace("café".encode(), "cafe\u0301".encode(), 1), "NFC"),
    ],
)
def test_known_answer_strict_parser_rejects_nonpersistent_bytes(
    mutation: Callable[[bytes], bytes],
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = mutation(KNOWN_ANSWER_PATH.read_bytes())
    assert type(raw) is bytes
    monkeypatch.setattr(codegen, "_KNOWN_ANSWER_RAW_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(codegen, "_KNOWN_ANSWER_SIZE_BYTES", len(raw))

    with pytest.raises(codegen.VisualPromptProfileCodegenError, match=message):
        codegen._parse_known_answer_bytes(raw)


def test_known_answer_case_order_and_synthetic_coverage_are_frozen() -> None:
    value = _known_answer_value()
    cases = cast(list[dict[str, object]], value["cases"])

    assert [case["case_id"] for case in cases] == [
        "character-reference-basic",
        "narrative-shot-unicode",
        "scene-reference-basic",
    ]
    assert len(cases) == 3
    narrative = cast(dict[str, object], cases[1]["render_input"])
    assert len(cast(list[object], narrative["character_asset_bindings"])) == 2
    dialogue = cast(list[dict[str, object]], narrative["dialogue"])
    assert [line["ordinal"] for line in dialogue] == [10, 20]
    assert any(ord(character) > 127 for character in json.dumps(narrative, ensure_ascii=False))
    assert unicodedata.normalize("NFC", json.dumps(narrative, ensure_ascii=False)) == json.dumps(
        narrative,
        ensure_ascii=False,
    )
    assert cast(dict[str, object], cases[2]["render_input"])["props"] == []

    catalog = load_visual_prompt_profile_source()
    roles = {
        role.value for entry in catalog.profiles for role in entry.profile.reference_asset_types
    }
    assert roles == {
        "CHARACTER_EXPRESSION_REFERENCE",
        "CHARACTER_IDENTITY_SHEET",
        "CHARACTER_POSE_REFERENCE",
        "SCENE_ESTABLISHING_REFERENCE",
        "SCENE_LIGHTING_REFERENCE",
        "SCENE_MATERIAL_REFERENCE",
        "SCENE_PROP_PLACEMENT_REFERENCE",
    }


def test_known_answer_hashes_use_independent_encoders_and_literal_domains() -> None:
    cases = cast(list[dict[str, object]], _known_answer_value()["cases"])
    for case in cases:
        render_input = case["render_input"]
        input_digest = hashlib.sha256(
            RENDER_INPUT_DOMAIN + _canonical_compact(render_input)
        ).hexdigest()
        prompt = cast(str, case["prompt_text"]).encode("utf-8")
        prompt_digest = hashlib.sha256(prompt).hexdigest()
        receipt = cast(dict[str, object], case["prompt_render_receipt"])
        receipt_projection = {
            key: value for key, value in receipt.items() if key != "prompt_render_receipt_sha256"
        }
        receipt_digest = hashlib.sha256(
            PROMPT_RECEIPT_DOMAIN + _canonical_compact(receipt_projection)
        ).hexdigest()

        assert case["render_input_sha256"] == input_digest
        assert case["prompt_sha256"] == prompt_digest
        assert case["prompt_size_bytes"] == len(prompt)
        assert receipt["render_input_sha256"] == input_digest
        assert receipt["prompt_sha256"] == prompt_digest
        assert receipt["prompt_render_receipt_sha256"] == receipt_digest
        assert hashlib.sha256(_canonical_compact(render_input)).hexdigest() != input_digest
        assert hashlib.sha256(PROMPT_RECEIPT_DOMAIN + prompt).hexdigest() != prompt_digest


def test_expected_fixtures_are_recomputed_and_authored_prompt_drift_fails(
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for case in closure.cases:
        prefix = ROOT / "tests/fixtures/visual_prompt_profiles/generated" / case.case_id
        assert prefix.with_suffix(".prompt.txt").read_bytes() == case.prompt_bytes
        receipt_path = prefix.with_suffix(".prompt-render-receipt.json")
        assert receipt_path.read_bytes() == case.receipt_bytes

    value = _known_answer_value()
    cases = cast(list[dict[str, object]], value["cases"])
    cases[0]["prompt_text"] = f"{cases[0]['prompt_text']}drift\n"
    raw = _canonical_document(value)
    parsed = _with_frozen_fingerprint(monkeypatch, raw)
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="prompt_text"):
        codegen._verify_known_answer(parsed, closure.catalog)


def test_generated_catalog_is_exact_static_source_build_without_source_evidence(
    closure: codegen._ExpectedClosure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog_module = importlib.import_module("sdc.visual_prompt_catalog")
    assert catalog_module.VISUAL_PROMPT_CATALOG == closure.catalog
    assert {name for name in vars(catalog_module) if not name.startswith("__")} == {
        "VISUAL_PROMPT_CATALOG"
    }

    generated_raw = (ROOT / "src/sdc/visual_prompt_catalog.py").read_bytes()
    receipt = _receipt_value()
    assert receipt["source_sha256"].encode() not in generated_raw
    assert codegen._KNOWN_ANSWER_RAW_SHA256.encode() not in generated_raw
    assert cast(str, receipt["catalog_digest_receipt_sha256"]).encode() not in generated_raw

    monkeypatch.setattr(
        source_module,
        "load_visual_prompt_profile_source",
        lambda: pytest.fail("generated catalog imported the source loader"),
    )
    sys.modules.pop("sdc.visual_prompt_catalog", None)
    reloaded = importlib.import_module("sdc.visual_prompt_catalog")
    assert reloaded.VISUAL_PROMPT_CATALOG == closure.catalog

    generated_tree = ast.parse(generated_raw.decode("utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(generated_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "sdc.visual_prompt_profile_source" not in imported_modules


def test_generated_document_machine_blocks_equal_the_fresh_source_view(
    closure: codegen._ExpectedClosure,
) -> None:
    expected = codegen._generated_view(closure.catalog)
    operator = _machine_block(
        (ROOT / "docs/reference/visual-prompt-profiles.md").read_bytes(),
        codegen._OPERATOR_BLOCK_BEGIN,
        codegen._OPERATOR_BLOCK_END,
    )
    agent_path = ROOT / "docs/reference/visual-prompt-agent-authoring.md"
    agent_raw = agent_path.read_bytes()
    agent = _machine_block(
        agent_raw,
        codegen._AGENT_BLOCK_BEGIN,
        codegen._AGENT_BLOCK_END,
    )

    assert operator == expected
    assert agent == expected
    assert b"Recommendation is advisory only" in agent_raw
    assert b"cannot select a profile, trigger rendering" in agent_raw


def test_catalog_digest_receipt_binds_every_nonself_leaf_with_literal_domain() -> None:
    document = _receipt_value()
    self_digest = cast(str, document.pop("catalog_digest_receipt_sha256"))
    baseline = hashlib.sha256(CATALOG_RECEIPT_DOMAIN + _canonical_compact(document)).hexdigest()

    assert self_digest == baseline
    assert "catalog_digest_receipt_sha256" not in document
    for path in _leaf_paths(document):
        mutated = _mutate_leaf(document, path)
        assert (
            hashlib.sha256(CATALOG_RECEIPT_DOMAIN + _canonical_compact(mutated)).hexdigest()
            != baseline
        ), path


def test_catalog_digest_receipt_uses_raw_byte_hashes_and_zero_authority(
    closure: codegen._ExpectedClosure,
) -> None:
    receipt = _receipt_value()
    assert receipt["source_path"] == VISUAL_PROMPT_SOURCE_PATH
    assert receipt["source_sha256"] == hashlib.sha256(closure.source_raw).hexdigest()
    assert receipt["source_size_bytes"] == len(closure.source_raw)
    assert receipt["reviewed_known_answer_path"] == VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH
    assert (
        receipt["reviewed_known_answer_sha256"]
        == hashlib.sha256(closure.known_answer_raw).hexdigest()
    )
    assert receipt["reviewed_known_answer_size_bytes"] == len(closure.known_answer_raw)
    artifacts = cast(list[dict[str, object]], receipt["generated_artifacts"])
    assert [item["artifact_path"] for item in artifacts] == list(
        VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS
    )
    assert CATALOG_RECEIPT_PATH.relative_to(ROOT).as_posix() not in {
        item["artifact_path"] for item in artifacts
    }
    for artifact in artifacts:
        raw = (ROOT / cast(str, artifact["artifact_path"])).read_bytes()
        assert artifact["artifact_sha256"] == hashlib.sha256(raw).hexdigest()
        assert artifact["artifact_size_bytes"] == len(raw)

    for field in (
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
    ):
        assert receipt[field] is False
    for field in (
        "authorized_attempts",
        "authorized_cost_cny",
        "posts_allowed",
        "provider_requests",
    ):
        assert type(receipt[field]) is int and receipt[field] == 0


def test_reviewed_catalog_admission_does_not_create_provider_authority() -> None:
    catalog = load_visual_prompt_profile_source()
    for entry in catalog.profiles:
        assert (
            entry.offline_render_admission_status
            is OfflineRenderAdmissionStatus.HUMAN_REVIEWED_FOR_OFFLINE_RENDER
        )
        assert (
            entry.profile_text_provenance_status
            is ProfileTextProvenanceStatus.FIRST_PARTY_TEXT_REVIEWED
        )
        assert entry.provider_syntax_compatibility_observations == ()
        assert entry.grants_rights is False
        assert entry.grants_qualification is False
        assert entry.grants_execution_authority is False
        assert entry.eligible_for_asset_promotion is False
    assert catalog.generation_authorized is False
    assert catalog.execution_authorized is False
    assert catalog.provider_requests == 0


def test_check_mode_is_byte_and_timestamp_read_only() -> None:
    paths = (
        *VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
        "docs/reference/visual-prompt-catalog-digest-receipt.json",
        VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,
    )
    before = _file_snapshot(ROOT, paths)

    assert codegen.main(["--check"]) == 0
    assert codegen.main(["--check"]) == 0

    assert _file_snapshot(ROOT, paths) == before


def test_update_writes_only_fixed_allowlist_and_never_known_answer(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
) -> None:
    known_answer = tmp_path / VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH
    known_answer.parent.mkdir(parents=True)
    known_answer.write_bytes(closure.known_answer_raw)
    unrelated = tmp_path / "unrelated.keep"
    unrelated.write_bytes(b"keep\n")
    before_known = _file_snapshot(tmp_path, (VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,))

    _materialize(tmp_path, closure)

    assert _file_snapshot(tmp_path, (VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,)) == before_known
    assert unrelated.read_bytes() == b"keep\n"
    actual = {
        path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()
    }
    assert actual == {
        *VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
        "docs/reference/visual-prompt-catalog-digest-receipt.json",
        VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,
        "unrelated.keep",
    }


@pytest.mark.parametrize("drift", ["missing", "extra", "byte", "receipt-order"])
def test_check_fails_closed_for_incomplete_or_drifted_closure(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
    drift: str,
) -> None:
    _materialize(tmp_path, closure)
    first_path = tmp_path / VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS[0]
    if drift == "missing":
        first_path.unlink()
    elif drift == "extra":
        (tmp_path / codegen._GENERATED_FIXTURE_DIRECTORY / "extra.fixture").write_bytes(b"x")
    elif drift == "byte":
        first_path.write_bytes(first_path.read_bytes() + b"x")
    else:
        receipt_path = tmp_path / "docs/reference/visual-prompt-catalog-digest-receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        receipt["generated_artifacts"].reverse()
        receipt_path.write_bytes(_canonical_document(receipt))

    with pytest.raises(codegen.VisualPromptProfileCodegenError):
        codegen._check_closure(tmp_path, closure)


def test_update_refuses_extra_generated_files_without_deleting_them(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
) -> None:
    _materialize(tmp_path, closure)
    extra = tmp_path / codegen._GENERATED_FIXTURE_DIRECTORY / "unapproved.txt"
    extra.write_bytes(b"preserve\n")

    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="unexpected"):
        codegen._update_closure(tmp_path, closure)

    assert extra.read_bytes() == b"preserve\n"


def test_paths_reject_alias_duplicate_self_and_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="outside"):
        codegen._replace_artifact(tmp_path, "../outside.txt", b"x")

    monkeypatch.setattr(
        codegen, "VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS", (*original[:-1], original[0])
    )
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="allowlist"):
        codegen._assert_fixed_allowlist()

    monkeypatch.setattr(
        codegen,
        "VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS",
        tuple(sorted((*original[:-1], "a/../b"))),
    )
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="canonical"):
        codegen._assert_fixed_allowlist()

    monkeypatch.setattr(
        codegen,
        "VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS",
        tuple(sorted((*original[:-1], codegen._CATALOG_RECEIPT_PATH))),
    )
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="itself"):
        codegen._assert_fixed_allowlist()


def test_stable_reader_and_artifact_check_reject_symlinks(
    tmp_path: Path,
    closure: codegen._ExpectedClosure,
) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(target)
    except OSError:
        pytest.skip("this host does not permit a test symlink")
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="non-symlink"):
        codegen._read_stable_regular_file(alias, max_bytes=100, label="test alias")

    broken_root = tmp_path / "broken-destination"
    broken_destination = broken_root / VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS[0]
    broken_destination.parent.mkdir(parents=True)
    broken_destination.symlink_to(tmp_path / "missing-target")
    with pytest.raises(codegen.VisualPromptProfileCodegenError, match="non-symlink"):
        codegen._replace_artifact(
            broken_root,
            VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS[0],
            b"replacement\n",
        )
    assert broken_destination.is_symlink()

    closure_root = tmp_path / "closure"
    closure_root.mkdir()
    _materialize(closure_root, closure)
    artifact = closure_root / VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS[0]
    artifact.unlink()
    artifact.symlink_to(target)
    with pytest.raises(codegen.VisualPromptProfileCodegenError):
        codegen._check_closure(closure_root, closure)


def test_cli_has_only_explicit_modes_and_root_is_cwd_environment_independent(
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
    monkeypatch.setenv("SDC_VISUAL_PROMPT_ROOT", str(tmp_path))
    assert codegen._repository_root() == expected == ROOT


def test_schema_boundary_reflects_the_accepted_compiler_integration_append() -> None:
    assert len(schemas.MODELS) == 83


def test_codegen_has_no_network_provider_credentials_clock_or_dynamic_execution() -> None:
    source = Path(codegen.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "__import__",
                "eval",
                "exec",
                "open",
            }:
                forbidden_calls.append(node.func.id)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"date", "datetime", "time"}
                and node.func.attr in {"now", "today", "utcnow", "time"}
            ):
                forbidden_calls.append(f"{node.func.value.id}.{node.func.attr}")

    assert imported_roots <= {
        "__future__",
        "argparse",
        "dataclasses",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "sdc",
        "stat",
        "tomllib",
        "typing",
        "unicodedata",
    }
    assert forbidden_calls == []
    assert all(
        forbidden not in source.casefold()
        for forbidden in ("requests.", "urllib", "socket", "subprocess", "api_key")
    )
