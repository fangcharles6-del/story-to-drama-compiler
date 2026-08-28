"""Fixed repository-only known-answer closure for the ADR-042 reference Prompt Compiler.

The generator has exactly two explicit modes.  It reads the frozen, human-reviewed source
packet and either checks or directly rewrites the single derived fixture.  It never writes the
source packet, creates a directory or uses a temporary path.  It performs no network, Provider,
credential, clock, random, Runtime, Candidate, Rights, Qualification or media operation.
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

from pydantic import ValidationError

from sdc import visual_reference_prompt_compiler as compiler_module
from sdc.contracts import CharacterBible, SceneBible
from sdc.visual_reference_prompt_compiler import (
    CreativeSampleReferenceVisualPromptCompileRequestV1,
    VisualReferencePromptCompilerError,
    compile_creative_sample_reference_visual_prompt,
)

_KNOWN_ANSWER_VERSION = "1.0.0"
_REVIEWED_SOURCE_PATH = (
    "tests/fixtures/visual_prompt_profiles/reference-compiler/reviewed-known-answer-source-v1.json"
)
_DERIVED_FIXTURE_PATH = (
    "tests/fixtures/visual_prompt_profiles/reference-compiler/generated-known-answer-v1.json"
)
_REVIEWED_SOURCE_RAW_SHA256 = "be072fe5be5ef4b35c2e482db3e60c14641bce8cf80eb95398d9a4468750170c"
_REVIEWED_SOURCE_SIZE_BYTES = 14_587
_MAX_SOURCE_BYTES = 1_048_576
_MAX_DERIVED_BYTES = 2_359_296
_MAX_REPOSITORY_METADATA_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 16
_MAX_JSON_CONTAINER_ITEMS = 64
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"
_CASE_IDS = (
    "character-reference-basic",
    "character-reference-unicode-nfc",
    "scene-reference-basic-empty-props",
    "scene-reference-unicode-nfc-multi-props",
)
_SOURCE_ROOT_KEYS = ("cases", "known_answer_version")
_SOURCE_CASE_KEYS = ("case_id", "request", "subject")
_DERIVED_CASE_KEYS = ("artifact", "case_id")


class VisualReferencePromptCompilerCodegenError(ValueError):
    """The fixed ADR-042 known-answer closure is missing, stale, unsafe or invalid."""


def _fail(message: str) -> Never:
    raise VisualReferencePromptCompilerCodegenError(message)


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


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _open_read_flags() -> int:
    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail("this host cannot enforce non-symlink fixture reads")
        flags |= no_follow
    return flags


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail(f"{label} has an invalid byte boundary")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(f"{label} could not be inspected") from exc
    if not _is_regular_non_symlink(before) or before.st_nlink != 1:
        _fail(f"{label} must be one regular non-symlink file with one link")
    if not 0 <= before.st_size <= max_bytes:
        _fail(f"{label} exceeds its byte boundary")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, _open_read_flags())
        opened = os.fstat(descriptor)
        if (
            not _is_regular_non_symlink(opened)
            or opened.st_nlink != 1
            or not _same_file(before, opened)
        ):
            _fail(f"{label} changed before it was opened")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                _fail(f"{label} exceeds its byte boundary")
        after_handle = os.fstat(descriptor)
    except VisualReferencePromptCompilerCodegenError:
        raise
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(f"{label} could not be read") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            f"{label} could not be re-inspected"
        ) from exc
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or _file_identity(before) != _file_identity(after_handle)
        or _file_identity(before) != _file_identity(after_path)
    ):
        _fail(f"{label} changed while it was read")
    raw = b"".join(chunks)
    if len(raw) != before.st_size:
        _fail(f"{label} byte count changed while it was read")
    return raw


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("persistent JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> Never:
    _fail(f"persistent JSON contains the non-finite number {value}")


def _validate_json_value(value: object, *, depth: int = 1) -> None:
    if depth > _MAX_JSON_CONTAINER_DEPTH:
        _fail("persistent JSON exceeds the frozen container-depth boundary")
    if value is None or type(value) in {bool, int}:
        return
    if type(value) is str:
        text = value
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            _fail("persistent JSON contains a non-Unicode-scalar string")
        if unicodedata.normalize("NFC", text) != text:
            _fail("persistent JSON strings must already use Unicode NFC")
        return
    if type(value) is list:
        array_items = cast(list[object], value)
        if len(array_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON array exceeds the frozen 64-item boundary")
        for item in array_items:
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        object_items = cast(dict[object, object], value)
        if len(object_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON object exceeds the frozen 64-field boundary")
        for key, item in object_items.items():
            if type(key) is not str:
                _fail("persistent JSON object keys must be exact strings")
            _validate_json_value(key, depth=depth)
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    _fail("persistent JSON contains a value outside the canonical type set")


def _canonical_document_bytes(value: object) -> bytes:
    _validate_json_value(value)
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
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "persistent JSON serialization failed"
        ) from exc


def _parse_canonical_document(raw: bytes, *, label: str) -> dict[str, object]:
    if not raw or raw.startswith(_UTF8_BOM) or b"\r" in raw:
        _fail(f"{label} must use nonempty UTF-8, LF-only, no-BOM bytes")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(f"{label} must end with exactly one LF")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisualReferencePromptCompilerCodegenError(
            f"{label} is not strict UTF-8 JSON"
        ) from exc
    if type(value) is not dict:
        _fail(f"{label} must have an object root")
    _validate_json_value(value)
    if _canonical_document_bytes(value) != raw:
        _fail(f"{label} is not the frozen persistent canonical JSON document")
    return cast(dict[str, object], value)


def _compact_model_json(value: dict[str, object]) -> bytes:
    _validate_json_value(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _validate_source_document(value: dict[str, object]) -> tuple[dict[str, object], ...]:
    if tuple(value) != _SOURCE_ROOT_KEYS:
        _fail("reviewed source root keys are not the frozen exact set")
    if value["known_answer_version"] != _KNOWN_ANSWER_VERSION:
        _fail("reviewed source known_answer_version is not frozen")
    raw_cases = value["cases"]
    if type(raw_cases) is not list:
        _fail("reviewed source cases must be one JSON array")
    cases = tuple(cast(list[object], raw_cases))
    if len(cases) != len(_CASE_IDS):
        _fail("reviewed source must contain exactly four cases")
    validated: list[dict[str, object]] = []
    for expected_id, raw_case in zip(_CASE_IDS, cases, strict=True):
        if type(raw_case) is not dict:
            _fail("each reviewed source case must be one object")
        case = cast(dict[str, object], raw_case)
        if tuple(case) != _SOURCE_CASE_KEYS or case.get("case_id") != expected_id:
            _fail("reviewed source case keys or order are not frozen")
        if type(case["request"]) is not dict or type(case["subject"]) is not dict:
            _fail("each reviewed source case must contain complete Request and subject objects")
        validated.append(case)
    return tuple(validated)


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    source_raw: bytes
    source_value: dict[str, object]
    derived_value: dict[str, object]
    derived_raw: bytes


def _load_reviewed_source(root: Path) -> tuple[bytes, dict[str, object]]:
    source_path = _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )
    raw = _read_stable_regular_file(
        source_path,
        max_bytes=_MAX_SOURCE_BYTES,
        label="reviewed known-answer source",
    )
    _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )
    if len(raw) != _REVIEWED_SOURCE_SIZE_BYTES:
        _fail("reviewed known-answer source byte size does not match its frozen constant")
    if hashlib.sha256(raw).hexdigest() != _REVIEWED_SOURCE_RAW_SHA256:
        _fail("reviewed known-answer source SHA-256 does not match its frozen constant")
    value = _parse_canonical_document(raw, label="reviewed known-answer source")
    _validate_source_document(value)
    return raw, value


def _build_expected_derived_value(source_value: dict[str, object]) -> dict[str, object]:
    cases = _validate_source_document(source_value)
    derived_cases: list[dict[str, object]] = []
    for case in cases:
        case_id = cast(str, case["case_id"])
        request_value = cast(dict[str, object], case["request"])
        subject_value = cast(dict[str, object], case["subject"])
        try:
            request = CreativeSampleReferenceVisualPromptCompileRequestV1.model_validate_json(
                _compact_model_json(request_value),
                strict=True,
            )
            purpose = request_value.get("asset_purpose")
            if purpose == "CHARACTER_REFERENCE_ASSET":
                subject: CharacterBible | SceneBible = CharacterBible.model_validate_json(
                    _compact_model_json(subject_value),
                    strict=True,
                )
            elif purpose == "SCENE_REFERENCE_ASSET":
                subject = SceneBible.model_validate_json(
                    _compact_model_json(subject_value),
                    strict=True,
                )
            else:
                _fail("reviewed source request has an unsupported asset purpose")
            artifact = compile_creative_sample_reference_visual_prompt(subject, request)
        except VisualReferencePromptCompilerCodegenError:
            raise
        except (
            ValidationError,
            VisualReferencePromptCompilerError,
            TypeError,
            ValueError,
            RecursionError,
        ) as exc:
            raise VisualReferencePromptCompilerCodegenError(
                f"reviewed source case failed deterministic compilation: {case_id}"
            ) from exc
        derived_case: dict[str, object] = {
            "artifact": artifact.model_dump(mode="json"),
            "case_id": case_id,
        }
        if tuple(derived_case) != _DERIVED_CASE_KEYS:
            _fail("internal derived case keys drifted")
        derived_cases.append(derived_case)
    return {
        "cases": derived_cases,
        "known_answer_version": _KNOWN_ANSWER_VERSION,
    }


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    _assert_fixed_paths()
    source_raw, source_value = _load_reviewed_source(root)
    derived_value = _build_expected_derived_value(source_value)
    derived_raw = _canonical_document_bytes(derived_value)
    if len(derived_raw) > _MAX_DERIVED_BYTES:
        _fail("derived known-answer fixture exceeds its byte boundary")
    return _ExpectedClosure(
        source_raw=source_raw,
        source_value=source_value,
        derived_value=derived_value,
        derived_raw=derived_raw,
    )


def _assert_fixed_paths() -> None:
    paths = (_REVIEWED_SOURCE_PATH, _DERIVED_FIXTURE_PATH)
    if len(set(paths)) != 2:
        _fail("source and derived fixture paths must be distinct")
    for value in paths:
        path = Path(value)
        if (
            path.is_absolute()
            or "\\" in value
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or ":" in path.parts[0]
        ):
            _fail("a fixed fixture path is not canonical repository-relative POSIX text")
    if Path(_REVIEWED_SOURCE_PATH).parent != Path(_DERIVED_FIXTURE_PATH).parent:
        _fail("source and derived fixture must share their frozen directory")


def _assert_parent_directory(path: Path) -> None:
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "derived fixture parent directory is missing or inaccessible"
        ) from exc
    if not _is_directory_non_symlink(info):
        _fail("derived fixture parent must be one regular non-symlink directory")


def _assert_safe_fixture_path(root: Path, relative_path: str, *, label: str) -> Path:
    if not root.is_absolute():
        _fail(f"{label} repository root must be absolute")
    current = root
    for part in ("", *Path(relative_path).parts[:-1]):
        if part:
            current /= part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise VisualReferencePromptCompilerCodegenError(
                f"{label} ancestor is missing or inaccessible"
            ) from exc
        if not _is_directory_non_symlink(info):
            _fail(f"{label} ancestors must be regular non-symlink directories")
    return root / relative_path


def _write_exact_derived(root: Path, relative_path: str, raw: bytes) -> None:
    if relative_path != _DERIVED_FIXTURE_PATH:
        _fail("update attempted to write outside the single fixed derived-fixture allowlist")
    destination = _assert_safe_fixture_path(
        root,
        relative_path,
        label="derived known-answer fixture",
    )
    source = _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )
    _assert_parent_directory(destination.parent)
    try:
        source_info = os.lstat(source)
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "reviewed source could not be inspected before update"
        ) from exc
    if not _is_regular_non_symlink(source_info) or source_info.st_nlink != 1:
        _fail("reviewed source must remain one regular non-symlink file")
    try:
        destination_before = os.lstat(destination)
    except FileNotFoundError:
        destination_before = None
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "derived fixture destination could not be inspected"
        ) from exc
    if destination_before is not None:
        if not _is_regular_non_symlink(destination_before) or destination_before.st_nlink != 1:
            _fail("derived fixture destination must be one regular non-symlink file")
        if _same_file(source_info, destination_before):
            _fail("derived fixture destination must not alias the reviewed source")
    flags = os.O_WRONLY
    if destination_before is None:
        flags |= os.O_CREAT | os.O_EXCL
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        flags |= int(getattr(os, "O_CLOEXEC", 0))
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            _fail("this host cannot enforce non-symlink fixture writes")
        flags |= no_follow
    descriptor: int | None = None
    try:
        descriptor = os.open(destination, flags, 0o644)
        opened = os.fstat(descriptor)
        if not _is_regular_non_symlink(opened) or opened.st_nlink != 1:
            _fail("opened derived fixture is not one regular file")
        if destination_before is not None and not _same_file(destination_before, opened):
            _fail("derived fixture destination changed before it was opened")
        if _same_file(source_info, opened):
            _fail("opened derived fixture aliases the reviewed source")
        os.ftruncate(descriptor, 0)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("derived fixture write made no progress")
            offset += written
        os.fsync(descriptor)
        after_handle = os.fstat(descriptor)
    except VisualReferencePromptCompilerCodegenError:
        raise
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "derived fixture could not be written directly"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(destination)
    except OSError as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "derived fixture could not be re-inspected"
        ) from exc
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or not _same_file(after_handle, after_path)
        or after_path.st_size != len(raw)
    ):
        _fail("derived fixture changed while it was written")
    _assert_safe_fixture_path(
        root,
        relative_path,
        label="derived known-answer fixture",
    )
    _assert_safe_fixture_path(
        root,
        _REVIEWED_SOURCE_PATH,
        label="reviewed known-answer source",
    )


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    derived_path = _assert_safe_fixture_path(
        root,
        _DERIVED_FIXTURE_PATH,
        label="derived known-answer fixture",
    )
    actual = _read_stable_regular_file(
        derived_path,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    _assert_safe_fixture_path(
        root,
        _DERIVED_FIXTURE_PATH,
        label="derived known-answer fixture",
    )
    _parse_canonical_document(actual, label="derived known-answer fixture")
    if actual != closure.derived_raw:
        _fail("derived known-answer fixture is byte-stale")


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    _write_exact_derived(root, _DERIVED_FIXTURE_PATH, closure.derived_raw)
    source_after, _source_value = _load_reviewed_source(root)
    if source_after != closure.source_raw:
        _fail("reviewed source changed during derived-fixture update")
    _check_closure(root, closure)


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_module_parent = root / "src" / "sdc"
    if module_path.parent != expected_module_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    expected_compiler_module = expected_module_parent / "visual_reference_prompt_compiler.py"
    if Path(compiler_module.__file__).resolve() != expected_compiler_module.resolve():
        _fail("Compiler module does not belong to the same fixed repository layout")
    pyproject_path = _assert_safe_fixture_path(
        root,
        "pyproject.toml",
        label="repository pyproject.toml",
    )
    raw = _read_stable_regular_file(
        pyproject_path,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise VisualReferencePromptCompilerCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m sdc.visual_reference_prompt_compiler_codegen",
        description="Check or explicitly update the fixed ADR-042 known-answer fixture.",
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
        _fail("one explicit codegen mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
