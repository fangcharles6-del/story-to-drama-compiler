"""Deterministic repository-only closure for visual Prompt profiles.

This module has exactly two explicit CLI modes. It reads only the frozen package source,
the manually reviewed known-answer document, and the fixed generated closure. It performs no
network, Provider, credential, clock, randomness, Compiler, Runtime, or asset operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Never, cast

from sdc import visual_prompt_profile_source as source_module
from sdc.visual_prompt_profile_source import _load_visual_prompt_profile_source_with_bytes
from sdc.visual_prompt_profiles import (
    VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
    VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,
    VISUAL_PROMPT_SOURCE_PATH,
    CatalogDigestReceipt,
    GeneratedArtifactDigest,
    PromptProfileCatalog,
    PromptRenderInput,
    _build_prompt_render_input_from_validated_value,
    build_catalog_digest_receipt,
    catalog_digest_receipt_document_projection,
    prompt_profile_catalog_projection,
    prompt_render_input_projection,
    prompt_render_input_sha256,
    prompt_render_receipt_document_projection,
    render_visual_prompt,
    resolve_visual_prompt_profile,
    visual_prompt_profile_projection,
)

_GENERATOR_ID = "sdc.visual-prompt-profile-generator"
_GENERATOR_VERSION = "1.0.0"
_KNOWN_ANSWER_VERSION = "1.0.0"
_KNOWN_ANSWER_RAW_SHA256 = "0b736f1759fc23e4e809f278f978843099cbe98b24e3a4a9359de5274b39ae75"
_KNOWN_ANSWER_SIZE_BYTES = 17_678
_CATALOG_RECEIPT_PATH = "docs/reference/visual-prompt-catalog-digest-receipt.json"
_MAX_KNOWN_ANSWER_BYTES = 262_144
_MAX_RECEIPT_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 16
_MAX_REPOSITORY_METADATA_BYTES = 1_048_576
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"
_KNOWN_ANSWER_CASE_IDS = (
    "character-reference-basic",
    "narrative-shot-unicode",
    "scene-reference-basic",
)
_GENERATED_FIXTURE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated"
_GENERATED_FIXTURE_NAMES = frozenset(
    path.rsplit("/", 1)[1]
    for path in VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS
    if path.startswith(f"{_GENERATED_FIXTURE_DIRECTORY}/")
)
_OPERATOR_BLOCK_BEGIN = "<!-- SDC-VISUAL-PROMPT-CATALOG-JSON:BEGIN -->"
_OPERATOR_BLOCK_END = "<!-- SDC-VISUAL-PROMPT-CATALOG-JSON:END -->"
_AGENT_BLOCK_BEGIN = "<!-- SDC-VISUAL-PROMPT-AGENT-JSON:BEGIN -->"
_AGENT_BLOCK_END = "<!-- SDC-VISUAL-PROMPT-AGENT-JSON:END -->"


class VisualPromptProfileCodegenError(ValueError):
    """The fixed repository closure is missing, stale, unsafe, or invalid."""


def _fail(message: str) -> Never:
    raise VisualPromptProfileCodegenError(message)


def _is_regular_non_symlink(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISREG(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
    )


def _is_directory_non_symlink(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISDIR(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
    )


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail(f"{label} has an invalid read boundary")
    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail(f"{label} cannot enforce a non-symlink read on this host")
        flags |= no_follow
        flags |= int(getattr(os, "O_CLOEXEC", 0))
    try:
        before = path.lstat()
        if not _is_regular_non_symlink(before) or before.st_size <= 0 or before.st_size > max_bytes:
            _fail(f"{label} must be one bounded regular non-symlink file")
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            opened = os.fstat(handle.fileno())
            if not _is_regular_non_symlink(opened) or _file_identity(opened) != _file_identity(
                before
            ):
                _fail(f"{label} changed before its read")
            raw = handle.read(max_bytes + 1)
            opened_after = os.fstat(handle.fileno())
        after = path.lstat()
    except VisualPromptProfileCodegenError:
        raise
    except OSError as exc:
        raise VisualPromptProfileCodegenError(f"{label} could not be read safely") from exc
    if (
        not _is_regular_non_symlink(opened_after)
        or not _is_regular_non_symlink(after)
        or _file_identity(opened_after) != _file_identity(before)
        or _file_identity(after) != _file_identity(before)
        or len(raw) != before.st_size
        or len(raw) > max_bytes
    ):
        _fail(f"{label} changed identity or size during its read")
    return raw


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_module_parent = root / "src" / "sdc"
    if module_path.parent != expected_module_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    expected_source_module = expected_module_parent / "visual_prompt_profile_source.py"
    if Path(source_module.__file__).resolve() != expected_source_module.resolve():
        _fail("source loader does not belong to the same fixed repository layout")
    pyproject_path = root / "pyproject.toml"
    raw = _read_stable_regular_file(
        pyproject_path,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise VisualPromptProfileCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _reject_json_constant(value: str) -> Never:
    _fail(f"known-answer non-finite JSON number is forbidden: {value}")


def _reject_json_float(value: str) -> Never:
    _fail(f"known-answer floating-point number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"known-answer duplicate key is forbidden: {key}")
        result[key] = value
    return result


def _validate_json_tree(value: object, *, depth: int) -> None:
    if type(value) is str:
        text = value
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            _fail("known-answer strings must contain Unicode scalar values")
        if unicodedata.normalize("NFC", text) != text:
            _fail("known-answer strings and keys must already be NFC")
        return
    if type(value) is list:
        if depth > _MAX_JSON_CONTAINER_DEPTH:
            _fail("known-answer exceeds the JSON depth limit")
        for item in cast(list[object], value):
            _validate_json_tree(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        if depth > _MAX_JSON_CONTAINER_DEPTH:
            _fail("known-answer exceeds the JSON depth limit")
        for key, item in cast(dict[str, object], value).items():
            if unicodedata.normalize("NFC", key) != key:
                _fail("known-answer strings and keys must already be NFC")
            _validate_json_tree(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )


def _canonical_document_bytes(value: object) -> bytes:
    try:
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
    except (TypeError, UnicodeError, ValueError) as exc:
        raise VisualPromptProfileCodegenError(
            "value is not a persistent canonical JSON document"
        ) from exc


def _parse_known_answer_bytes(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes or not raw or len(raw) > _MAX_KNOWN_ANSWER_BYTES:
        _fail("known-answer violates its exact byte boundary")
    if hashlib.sha256(raw).hexdigest() != _KNOWN_ANSWER_RAW_SHA256:
        _fail("known-answer raw SHA-256 does not match the frozen reviewed fingerprint")
    if len(raw) != _KNOWN_ANSWER_SIZE_BYTES:
        _fail("known-answer byte length does not match the frozen reviewed fingerprint")
    if raw.startswith(_UTF8_BOM):
        _fail("known-answer must not contain a BOM")
    if b"\r" in raw:
        _fail("known-answer must use LF only")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
        )
    except VisualPromptProfileCodegenError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise VisualPromptProfileCodegenError("known-answer must be strict UTF-8 JSON") from exc
    if type(value) is not dict:
        _fail("known-answer root must be one exact JSON object")
    root = cast(dict[str, object], value)
    _validate_json_tree(root, depth=1)
    if raw != _canonical_document_bytes(root):
        _fail("known-answer bytes are not persistent canonical JSON")
    return root


def _json_object(value: object, *, label: str, keys: frozenset[str]) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"{label} must be an exact JSON object")
    result = cast(dict[object, object], value)
    if any(type(key) is not str for key in result):
        _fail(f"{label} keys must be exact strings")
    typed = cast(dict[str, object], result)
    actual = frozenset(typed)
    if actual != keys:
        _fail(
            f"{label} has an invalid field set; "
            f"missing={sorted(keys - actual)}, unknown={sorted(actual - keys)}"
        )
    return typed


def _json_array(value: object, *, label: str) -> list[object]:
    if type(value) is not list:
        _fail(f"{label} must be an exact JSON array")
    return cast(list[object], value)


def _strict_equal(actual: object, expected: object, *, label: str) -> None:
    if type(actual) is not type(expected):
        _fail(f"{label} has a type-coerced value")
    if type(expected) is dict:
        actual_dict = cast(dict[str, object], actual)
        expected_dict = cast(dict[str, object], expected)
        if frozenset(actual_dict) != frozenset(expected_dict):
            _fail(f"{label} has missing or unknown fields")
        for key in expected_dict:
            _strict_equal(actual_dict[key], expected_dict[key], label=f"{label}.{key}")
        return
    if type(expected) is list:
        actual_list = cast(list[object], actual)
        expected_list = cast(list[object], expected)
        if len(actual_list) != len(expected_list):
            _fail(f"{label} has the wrong array length")
        for index, (actual_item, expected_item) in enumerate(
            zip(actual_list, expected_list, strict=True)
        ):
            _strict_equal(actual_item, expected_item, label=f"{label}[{index}]")
        return
    if actual != expected:
        _fail(f"{label} does not match the recomputed value")


def _validate_prompt_text(value: object) -> bytes:
    if type(value) is not str:
        _fail("known-answer prompt_text must be an exact string")
    text = value
    try:
        raw = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise VisualPromptProfileCodegenError(
            "known-answer prompt_text is not UTF-8 encodable"
        ) from exc
    if (
        unicodedata.normalize("NFC", text) != text
        or text.startswith("\ufeff")
        or "\r" in text
        or not text.endswith("\n")
        or text.endswith("\n\n")
        or not 1 <= len(raw) <= 65_536
        or any(line.endswith((" ", "\t")) for line in text[:-1].split("\n"))
    ):
        _fail("known-answer prompt_text violates the frozen PromptText codec")
    return raw


@dataclass(frozen=True, slots=True)
class _VerifiedKnownAnswerCase:
    case_id: str
    render_input: PromptRenderInput
    prompt_bytes: bytes
    receipt_bytes: bytes
    prompt_sha256: str
    prompt_render_receipt_sha256: str
    render_input_sha256: str


def _verify_known_answer(
    value: dict[str, object],
    catalog: PromptProfileCatalog,
) -> tuple[_VerifiedKnownAnswerCase, ...]:
    root = _json_object(
        value,
        label="known-answer root",
        keys=frozenset({"cases", "known_answer_version"}),
    )
    if (
        type(root["known_answer_version"]) is not str
        or root["known_answer_version"] != _KNOWN_ANSWER_VERSION
    ):
        _fail("known_answer_version must equal 1.0.0")
    cases = _json_array(root["cases"], label="known-answer cases")
    if len(cases) != 3:
        _fail("known-answer v1 must contain exactly three cases")
    case_keys = frozenset(
        {
            "case_id",
            "catalog_sha256",
            "catalog_version",
            "profile_id",
            "profile_sha256",
            "profile_version",
            "prompt_render_receipt",
            "prompt_sha256",
            "prompt_size_bytes",
            "prompt_text",
            "render_input",
            "render_input_sha256",
        }
    )
    verified: list[_VerifiedKnownAnswerCase] = []
    for index, raw_case in enumerate(cases):
        case = _json_object(
            raw_case,
            label=f"known-answer cases[{index}]",
            keys=case_keys,
        )
        case_id = case["case_id"]
        if type(case_id) is not str or case_id != _KNOWN_ANSWER_CASE_IDS[index]:
            _fail("known-answer case identities or order changed")
        profile_id = case["profile_id"]
        if type(profile_id) is not str:
            _fail(f"{case_id}.profile_id must be an exact string")
        matching_entries = tuple(
            entry for entry in catalog.profiles if entry.profile.profile_id == profile_id
        )
        if len(matching_entries) != 1:
            _fail(f"{case_id} does not resolve one initial catalog profile")
        entry = matching_entries[0]
        expected_identity = {
            "catalog_sha256": catalog.catalog_sha256,
            "catalog_version": catalog.catalog_version,
            "profile_id": entry.profile.profile_id,
            "profile_sha256": entry.profile_sha256,
            "profile_version": entry.profile.profile_version,
        }
        for key, expected in expected_identity.items():
            _strict_equal(case[key], expected, label=f"{case_id}.{key}")
        render_input = _build_prompt_render_input_from_validated_value(case["render_input"])
        render_projection = prompt_render_input_projection(render_input)
        _strict_equal(
            case["render_input"],
            render_projection,
            label=f"{case_id}.render_input",
        )
        input_digest = prompt_render_input_sha256(render_input)
        _strict_equal(
            case["render_input_sha256"],
            input_digest,
            label=f"{case_id}.render_input_sha256",
        )
        snapshot = resolve_visual_prompt_profile(
            catalog,
            catalog_version=catalog.catalog_version,
            catalog_sha256=catalog.catalog_sha256,
            profile_id=entry.profile.profile_id,
            profile_version=entry.profile.profile_version,
            profile_sha256=entry.profile_sha256,
        )
        prompt_bytes, receipt = render_visual_prompt(render_input, snapshot)
        authored_prompt_bytes = _validate_prompt_text(case["prompt_text"])
        if authored_prompt_bytes != prompt_bytes:
            _fail(f"{case_id}.prompt_text does not match the production pure renderer")
        prompt_digest = hashlib.sha256(prompt_bytes).hexdigest()
        _strict_equal(
            case["prompt_sha256"],
            prompt_digest,
            label=f"{case_id}.prompt_sha256",
        )
        _strict_equal(
            case["prompt_size_bytes"],
            len(prompt_bytes),
            label=f"{case_id}.prompt_size_bytes",
        )
        receipt_document = prompt_render_receipt_document_projection(receipt)
        _strict_equal(
            case["prompt_render_receipt"],
            receipt_document,
            label=f"{case_id}.prompt_render_receipt",
        )
        verified.append(
            _VerifiedKnownAnswerCase(
                case_id=case_id,
                render_input=render_input,
                prompt_bytes=prompt_bytes,
                receipt_bytes=_canonical_document_bytes(receipt_document),
                prompt_sha256=prompt_digest,
                prompt_render_receipt_sha256=receipt.prompt_render_receipt_sha256,
                render_input_sha256=input_digest,
            )
        )
    return tuple(verified)


def _generated_catalog_value(
    source_value: dict[str, object],
    catalog: PromptProfileCatalog,
) -> dict[str, object]:
    raw_profiles = _json_array(source_value["profiles"], label="source profiles")
    generated_profiles = [
        {
            **cast(dict[str, object], raw_entry),
            "profile_sha256": entry.profile_sha256,
        }
        for raw_entry, entry in zip(raw_profiles, catalog.profiles, strict=True)
    ]
    return {
        **source_value,
        "catalog_sha256": catalog.catalog_sha256,
        "profiles": generated_profiles,
    }


def _generated_catalog_python(value: dict[str, object]) -> bytes:
    document = _canonical_document_bytes(value).decode("utf-8")
    encoded = document.encode("utf-8").hex()
    chunks = [encoded[offset : offset + 72] for offset in range(0, len(encoded), 72)]
    literals = "\n".join(f'            "{part}"' for part in chunks)
    text = (
        '"""Generated static visual Prompt catalog. Do not edit by hand."""\n\n'
        "from json import loads as _loads\n\n"
        "from sdc.visual_prompt_profiles import (\n"
        "    _build_catalog_from_generated_value as _build_catalog,\n"
        ")\n\n"
        "VISUAL_PROMPT_CATALOG = _build_catalog(\n"
        "    _loads(\n"
        "        bytes.fromhex(\n"
        f"{literals}\n"
        "        )\n"
        "    )\n"
        ")\n"
        "del _build_catalog, _loads\n"
    )
    return text.encode("utf-8")


def _generated_view(catalog: PromptProfileCatalog) -> dict[str, object]:
    return {
        "catalog_projection": prompt_profile_catalog_projection(catalog),
        "profiles": [visual_prompt_profile_projection(entry.profile) for entry in catalog.profiles],
    }


def _operator_markdown(view: dict[str, object]) -> bytes:
    block = _canonical_document_bytes(view).decode("utf-8")
    text = (
        "# Visual Prompt Profiles\n\n"
        "Generated operator reference for the exact offline deterministic catalog. "
        "This document grants no Provider, execution, rights, qualification, publication, "
        "training, or asset-promotion authority.\n\n"
        f"{_OPERATOR_BLOCK_BEGIN}\n"
        "\x60\x60\x60json\n"
        f"{block}"
        "\x60\x60\x60\n"
        f"{_OPERATOR_BLOCK_END}\n"
    )
    return text.encode("utf-8")


def _agent_markdown(view: dict[str, object]) -> bytes:
    block = _canonical_document_bytes(view).decode("utf-8")
    text = (
        "# Visual Prompt Agent Authoring Reference\n\n"
        "Recommendation is advisory only. An Agent cannot select a profile, trigger rendering, "
        "choose a Provider, initiate execution, or grant rights, qualification, publication, "
        "training, spending, or asset promotion.\n\n"
        f"{_AGENT_BLOCK_BEGIN}\n"
        "\x60\x60\x60json\n"
        f"{block}"
        "\x60\x60\x60\n"
        f"{_AGENT_BLOCK_END}\n"
    )
    return text.encode("utf-8")


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    catalog: PromptProfileCatalog
    source_raw: bytes
    known_answer_raw: bytes
    cases: tuple[_VerifiedKnownAnswerCase, ...]
    generated_artifacts: tuple[tuple[str, bytes], ...]
    catalog_receipt: CatalogDigestReceipt
    catalog_receipt_bytes: bytes


def _assert_fixed_allowlist() -> None:
    if (
        len(VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS) != 9
        or len(set(VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS)) != 9
        or VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS
        != tuple(sorted(VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS))
    ):
        _fail("generated artifact allowlist is not the frozen unique Unicode order")
    if _CATALOG_RECEIPT_PATH in VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS:
        _fail("Catalog Digest Receipt must not list or hash itself")
    for path in (
        *VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS,
        _CATALOG_RECEIPT_PATH,
        VISUAL_PROMPT_SOURCE_PATH,
        VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH,
    ):
        candidate = Path(path)
        if (
            candidate.is_absolute()
            or "\\" in path
            or not candidate.parts
            or any(part in {"", ".", ".."} for part in candidate.parts)
            or ":" in candidate.parts[0]
        ):
            _fail("a fixed closure path is not one canonical repository-relative path")


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    _assert_fixed_allowlist()
    source_raw, catalog = _load_visual_prompt_profile_source_with_bytes()
    source_path = root / VISUAL_PROMPT_SOURCE_PATH
    if Path(source_module.__file__).with_name("visual_prompt_profiles.json").resolve() != (
        source_path.resolve()
    ):
        _fail("the package-relative source is not the frozen repository source")
    known_answer_path = root / VISUAL_PROMPT_REVIEWED_KNOWN_ANSWER_PATH
    known_answer_raw = _read_stable_regular_file(
        known_answer_path,
        max_bytes=_MAX_KNOWN_ANSWER_BYTES,
        label="reviewed known-answer",
    )
    known_answer_value = _parse_known_answer_bytes(known_answer_raw)
    cases = _verify_known_answer(known_answer_value, catalog)
    source_value = json.loads(source_raw.decode("utf-8"))
    if type(source_value) is not dict:
        _fail("strict source unexpectedly lost its object root")
    generated_catalog = _generated_catalog_python(
        _generated_catalog_value(cast(dict[str, object], source_value), catalog)
    )
    view = _generated_view(catalog)
    case_by_id = {case.case_id: case for case in cases}
    artifact_bytes: dict[str, bytes] = {
        "docs/reference/visual-prompt-agent-authoring.md": _agent_markdown(view),
        "docs/reference/visual-prompt-profiles.md": _operator_markdown(view),
        "src/sdc/visual_prompt_catalog.py": generated_catalog,
    }
    for case_id in _KNOWN_ANSWER_CASE_IDS:
        case = case_by_id[case_id]
        fixture_prefix = f"{_GENERATED_FIXTURE_DIRECTORY}/{case_id}"
        artifact_bytes[f"{fixture_prefix}.prompt-render-receipt.json"] = case.receipt_bytes
        artifact_bytes[f"{fixture_prefix}.prompt.txt"] = case.prompt_bytes
    if tuple(sorted(artifact_bytes)) != VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS:
        _fail("in-memory generated artifact closure does not match the frozen allowlist")
    generated_artifacts = tuple(
        (path, artifact_bytes[path]) for path in VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS
    )
    artifact_digests = tuple(
        GeneratedArtifactDigest(
            artifact_path=path,
            artifact_sha256=hashlib.sha256(raw).hexdigest(),
            artifact_size_bytes=len(raw),
        )
        for path, raw in generated_artifacts
    )
    receipt = build_catalog_digest_receipt(
        source_sha256=hashlib.sha256(source_raw).hexdigest(),
        source_size_bytes=len(source_raw),
        catalog=catalog,
        generated_artifacts=artifact_digests,
        reviewed_known_answer_sha256=hashlib.sha256(known_answer_raw).hexdigest(),
        reviewed_known_answer_size_bytes=len(known_answer_raw),
    )
    receipt_bytes = _canonical_document_bytes(catalog_digest_receipt_document_projection(receipt))
    if len(receipt_bytes) > _MAX_RECEIPT_BYTES:
        _fail("Catalog Digest Receipt exceeds its byte limit")
    return _ExpectedClosure(
        catalog=catalog,
        source_raw=source_raw,
        known_answer_raw=known_answer_raw,
        cases=cases,
        generated_artifacts=generated_artifacts,
        catalog_receipt=receipt,
        catalog_receipt_bytes=receipt_bytes,
    )


def _assert_generated_directory(
    root: Path,
    *,
    require_complete: bool,
) -> None:
    directory = root / _GENERATED_FIXTURE_DIRECTORY
    if not directory.exists():
        if require_complete:
            _fail("generated fixture directory is missing")
        return
    info = directory.lstat()
    if not _is_directory_non_symlink(info):
        _fail("generated fixture directory must be a regular non-symlink directory")
    try:
        with os.scandir(directory) as scan:
            entries = tuple(sorted(scan, key=lambda item: item.name))
    except OSError as exc:
        raise VisualPromptProfileCodegenError(
            "generated fixture directory could not be inspected"
        ) from exc
    actual_names = frozenset(entry.name for entry in entries)
    extras = actual_names - _GENERATED_FIXTURE_NAMES
    if extras:
        _fail(f"generated fixture directory contains unexpected entries: {sorted(extras)}")
    if require_complete and actual_names != _GENERATED_FIXTURE_NAMES:
        _fail("generated fixture directory is missing an expected file")
    for entry in entries:
        info = entry.stat(follow_symlinks=False)
        if not _is_regular_non_symlink(info):
            _fail("generated fixture entries must be regular non-symlink files")


def _read_exact_artifact(root: Path, relative_path: str) -> bytes:
    return _read_stable_regular_file(
        root / relative_path,
        max_bytes=_MAX_RECEIPT_BYTES,
        label=f"generated artifact {relative_path}",
    )


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    _assert_generated_directory(root, require_complete=True)
    for path, expected in closure.generated_artifacts:
        if _read_exact_artifact(root, path) != expected:
            _fail(f"generated artifact is byte-stale: {path}")
    if _read_exact_artifact(root, _CATALOG_RECEIPT_PATH) != closure.catalog_receipt_bytes:
        _fail("Catalog Digest Receipt is byte-stale")


def _ensure_parent_directories(root: Path, relative_path: str) -> Path:
    current = root
    parts = Path(relative_path).parts
    for part in parts[:-1]:
        current = current / part
        if current.exists():
            if not _is_directory_non_symlink(current.lstat()):
                _fail("generated artifact parent must be a regular non-symlink directory")
        else:
            try:
                current.mkdir()
            except OSError as exc:
                raise VisualPromptProfileCodegenError(
                    "generated artifact parent could not be created"
                ) from exc
    return root / relative_path


def _replace_artifact(root: Path, relative_path: str, raw: bytes) -> None:
    allowed = frozenset((*VISUAL_PROMPT_GENERATED_ARTIFACT_PATHS, _CATALOG_RECEIPT_PATH))
    if relative_path not in allowed:
        _fail("update attempted to write outside the fixed artifact allowlist")
    destination = _ensure_parent_directories(root, relative_path)
    try:
        destination_info = destination.lstat()
    except FileNotFoundError:
        pass
    else:
        if not _is_regular_non_symlink(destination_info):
            _fail("generated artifact destination must be a regular non-symlink file")
    temporary = destination.with_name(f".{destination.name}.sdc-visual-prompt-update")
    if temporary.exists():
        _fail("deterministic update temporary path already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail("this host cannot enforce non-symlink artifact creation")
        flags |= no_follow
    created = False
    try:
        descriptor = os.open(temporary, flags, 0o644)
        created = True
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        created = False
    except OSError as exc:
        raise VisualPromptProfileCodegenError(
            f"generated artifact could not be replaced: {relative_path}"
        ) from exc
    finally:
        if created:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    _assert_generated_directory(root, require_complete=False)
    for path, raw in closure.generated_artifacts:
        _replace_artifact(root, path, raw)
    _replace_artifact(root, _CATALOG_RECEIPT_PATH, closure.catalog_receipt_bytes)
    _check_closure(root, closure)


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sdc.visual_prompt_profile_codegen",
        description="Check or explicitly update the fixed visual Prompt profile closure.",
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--update", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    root = _repository_root()
    closure = _build_expected_closure(root)
    if args.check:
        _check_closure(root, closure)
    elif args.update:
        _update_closure(root, closure)
    else:  # pragma: no cover - argparse makes the modes exhaustive
        _fail("one explicit generator mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
