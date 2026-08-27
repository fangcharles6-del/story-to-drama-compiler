"""Strict package-relative loading for the visual Prompt profile source."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Never, cast
from unicodedata import normalize

from sdc.visual_prompt_profiles import (
    PromptProfileCatalog,
    VisualPromptProfileError,
    _build_catalog_from_validated_source,
)

__all__ = ("VisualPromptProfileSourceError", "load_visual_prompt_profile_source")

_SOURCE_FILE_NAME = "visual_prompt_profiles.json"
_MAX_SOURCE_JSON_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 16
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"


class VisualPromptProfileSourceError(ValueError):
    """The fixed visual Prompt profile source failed strict admission."""


def _reject_json_constant(value: str) -> Never:
    raise VisualPromptProfileSourceError(f"non-finite JSON number is forbidden: {value}")


def _reject_json_float(value: str) -> Never:
    raise VisualPromptProfileSourceError(f"JSON floating-point number is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise VisualPromptProfileSourceError(
                f"duplicate visual Prompt profile source key is forbidden: {key}"
            )
        result[key] = value
    return result


def _validate_json_tree(value: object, *, depth: int) -> None:
    if type(value) is str:
        text = value
        if normalize("NFC", text) != text:
            raise VisualPromptProfileSourceError(
                "visual Prompt profile source strings and keys must already be NFC"
            )
        return
    if type(value) is list:
        if depth > _MAX_JSON_CONTAINER_DEPTH:
            raise VisualPromptProfileSourceError(
                "visual Prompt profile source exceeds the JSON depth limit"
            )
        for item in cast(list[object], value):
            _validate_json_tree(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        if depth > _MAX_JSON_CONTAINER_DEPTH:
            raise VisualPromptProfileSourceError(
                "visual Prompt profile source exceeds the JSON depth limit"
            )
        for key, item in cast(dict[str, object], value).items():
            if normalize("NFC", key) != key:
                raise VisualPromptProfileSourceError(
                    "visual Prompt profile source strings and keys must already be NFC"
                )
            _validate_json_tree(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )


def _canonical_document_bytes(value: dict[str, object]) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return (text + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source is not canonically encodable"
        ) from exc


def _parse_visual_prompt_profile_source_bytes(raw: bytes) -> PromptProfileCatalog:
    """Parse injected source bytes without widening the production filesystem API."""

    if type(raw) is not bytes:
        raise VisualPromptProfileSourceError("visual Prompt profile source must be exact bytes")
    if not raw or len(raw) > _MAX_SOURCE_JSON_BYTES:
        raise VisualPromptProfileSourceError("visual Prompt profile source violates its byte limit")
    if raw.startswith(_UTF8_BOM):
        raise VisualPromptProfileSourceError("visual Prompt profile source must not contain a BOM")
    if b"\r" in raw:
        raise VisualPromptProfileSourceError("visual Prompt profile source must use LF only")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
        )
    except VisualPromptProfileSourceError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source must be strict UTF-8 JSON"
        ) from exc

    if type(value) is not dict:
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source root must be one JSON object"
        )
    source = cast(dict[str, object], value)
    _validate_json_tree(source, depth=1)
    if raw != _canonical_document_bytes(source):
        raise VisualPromptProfileSourceError("visual Prompt profile source bytes are not canonical")

    try:
        return _build_catalog_from_validated_source(source)
    except VisualPromptProfileError as exc:
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source violates its exact catalog contract"
        ) from exc


def _is_regular_non_symlink(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return (
        stat.S_ISREG(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and not bool(attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
    )


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _read_stable_regular_file(path: Path, *, max_bytes: int) -> bytes:
    if not isinstance(path, Path) or type(max_bytes) is not int or max_bytes <= 0:
        raise VisualPromptProfileSourceError("invalid fixed source read boundary")

    flags = os.O_RDONLY
    if os.name == "nt":
        flags |= int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOINHERIT", 0))
    else:
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if type(no_follow) is not int:
            raise VisualPromptProfileSourceError(
                "this host cannot enforce non-symlink source opening"
            )
        flags |= no_follow
        flags |= int(getattr(os, "O_CLOEXEC", 0))

    try:
        before = path.lstat()
        if not _is_regular_non_symlink(before) or before.st_size <= 0 or before.st_size > max_bytes:
            raise VisualPromptProfileSourceError(
                "visual Prompt profile source must be one bounded regular non-symlink file"
            )

        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb", closefd=True) as handle:
            opened = os.fstat(handle.fileno())
            if not _is_regular_non_symlink(opened) or _file_identity(opened) != _file_identity(
                before
            ):
                raise VisualPromptProfileSourceError(
                    "visual Prompt profile source changed before its read"
                )
            data = handle.read(max_bytes + 1)
            opened_after = os.fstat(handle.fileno())
        after = path.lstat()
    except VisualPromptProfileSourceError:
        raise
    except OSError as exc:
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source could not be read safely"
        ) from exc

    if (
        not _is_regular_non_symlink(opened_after)
        or not _is_regular_non_symlink(after)
        or _file_identity(opened_after) != _file_identity(before)
        or _file_identity(after) != _file_identity(before)
        or len(data) != before.st_size
        or len(data) > max_bytes
    ):
        raise VisualPromptProfileSourceError(
            "visual Prompt profile source changed identity or size during its read"
        )
    return data


def _read_visual_prompt_profile_source_bytes() -> bytes:
    source_path = Path(__file__).with_name(_SOURCE_FILE_NAME)
    return _read_stable_regular_file(source_path, max_bytes=_MAX_SOURCE_JSON_BYTES)


def _load_visual_prompt_profile_source_with_bytes() -> tuple[bytes, PromptProfileCatalog]:
    """Load one stable source byte stream and its strictly parsed catalog."""

    raw = _read_visual_prompt_profile_source_bytes()
    return raw, _parse_visual_prompt_profile_source_bytes(raw)


def load_visual_prompt_profile_source() -> PromptProfileCatalog:
    """Load the sole package-relative visual Prompt profile source."""

    _, catalog = _load_visual_prompt_profile_source_with_bytes()
    return catalog
