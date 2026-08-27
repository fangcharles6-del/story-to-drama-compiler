from __future__ import annotations

import copy
import inspect
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from sdc import visual_prompt_profile_source as source_module
from sdc.visual_prompt_profile_source import (
    VisualPromptProfileSourceError,
    _is_regular_non_symlink,
    _load_visual_prompt_profile_source_with_bytes,
    _parse_visual_prompt_profile_source_bytes,
    _read_stable_regular_file,
    load_visual_prompt_profile_source,
)
from sdc.visual_prompt_profiles import PromptProfileCatalog

SOURCE_PATH = Path(source_module.__file__).with_name("visual_prompt_profiles.json")


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


def _profiles(value: dict[str, object]) -> list[dict[str, object]]:
    profiles = value["profiles"]
    assert type(profiles) is list
    assert all(type(item) is dict for item in profiles)
    return cast(list[dict[str, object]], profiles)


def _profile(entry: dict[str, object]) -> dict[str, object]:
    profile = entry["profile"]
    assert type(profile) is dict
    return cast(dict[str, object], profile)


def test_fixed_package_source_loads_as_one_stable_byte_stream() -> None:
    raw, catalog = _load_visual_prompt_profile_source_with_bytes()

    assert raw == SOURCE_PATH.read_bytes()
    assert isinstance(catalog, PromptProfileCatalog)
    assert load_visual_prompt_profile_source() == catalog


def test_production_loader_has_no_path_or_environment_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "visual_prompt_profiles.json").write_bytes(b"not the package source")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDC_VISUAL_PROMPT_PROFILE_SOURCE", str(tmp_path))

    assert tuple(inspect.signature(load_visual_prompt_profile_source).parameters) == ()
    assert load_visual_prompt_profile_source() == _parse_visual_prompt_profile_source_bytes(
        SOURCE_PATH.read_bytes()
    )


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda raw: b"", "byte limit"),
        (lambda raw: b"\xef\xbb\xbf" + raw, "BOM"),
        (lambda raw: raw.replace(b"\n", b"\r\n"), "LF only"),
        (lambda raw: raw[:-1], "not canonical"),
        (lambda raw: raw + b"\n", "not canonical"),
        (lambda raw: b"\xff" + raw, "strict UTF-8 JSON"),
        (lambda raw: b"[]\n", "root must be one JSON object"),
        (
            lambda raw: raw.replace(
                b"{\n",
                b'{\n  "automated_execution_allowed": false,\n',
                1,
            ),
            "duplicate",
        ),
        (
            lambda raw: raw.replace(
                b'"authorized_attempts": 0',
                b'"authorized_attempts": 0.0',
                1,
            ),
            "floating-point",
        ),
        (
            lambda raw: raw.replace(
                b'"authorized_attempts": 0',
                b'"authorized_attempts": NaN',
                1,
            ),
            "non-finite",
        ),
    ],
)
def test_private_bytes_parser_rejects_noncanonical_json(
    mutate: Callable[[bytes], bytes], message: str
) -> None:
    raw = mutate(SOURCE_PATH.read_bytes())
    assert type(raw) is bytes

    with pytest.raises(VisualPromptProfileSourceError, match=message):
        _parse_visual_prompt_profile_source_bytes(raw)


def test_private_bytes_parser_requires_exact_bytes() -> None:
    with pytest.raises(VisualPromptProfileSourceError, match="exact bytes"):
        _parse_visual_prompt_profile_source_bytes(bytearray(SOURCE_PATH.read_bytes()))  # type: ignore[arg-type]


def test_private_bytes_parser_rejects_oversize_before_json_decode() -> None:
    with pytest.raises(VisualPromptProfileSourceError, match="byte limit"):
        _parse_visual_prompt_profile_source_bytes(b" " * 262_145)


def test_private_bytes_parser_uses_deterministic_byte_error_precedence() -> None:
    raw = b"\xef\xbb\xbf" + SOURCE_PATH.read_bytes().replace(b"\n", b"\r\n")

    with pytest.raises(VisualPromptProfileSourceError, match="BOM"):
        _parse_visual_prompt_profile_source_bytes(raw)


def test_private_bytes_parser_rejects_non_nfc_text() -> None:
    value = _source_value()
    _profiles(value)[0]["display_name"] = "Cafe\u0301"

    with pytest.raises(VisualPromptProfileSourceError, match="already be NFC"):
        _parse_visual_prompt_profile_source_bytes(_canonical_document(value))


def test_private_bytes_parser_rejects_excess_container_depth() -> None:
    value = _source_value()
    deep: object = []
    for _ in range(16):
        deep = [deep]
    value["unexpected_deep_value"] = deep

    with pytest.raises(VisualPromptProfileSourceError, match="depth limit"):
        _parse_visual_prompt_profile_source_bytes(_canonical_document(value))


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown-root-field",
        "missing-root-field",
        "coerced-counter",
        "coerced-boolean",
        "authority-literal",
        "profile-order",
        "duplicate-profile-identity",
        "unknown-profile-field",
        "unknown-taxonomy",
        "profile-renderer-version",
        "recipe-role-mismatch",
        "repeated-placeholder",
        "invalid-placeholder",
    ],
)
def test_private_bytes_parser_enforces_exact_shape_and_cross_field_closure(
    mutation: str,
) -> None:
    value = _source_value()
    entries = _profiles(value)
    if mutation == "unknown-root-field":
        value["unknown"] = False
    elif mutation == "missing-root-field":
        del value["source_revision"]
    elif mutation == "coerced-counter":
        value["authorized_attempts"] = False
    elif mutation == "coerced-boolean":
        value["generation_authorized"] = 0
    elif mutation == "authority-literal":
        value["provider_state"] = "AUTHORIZED"
    elif mutation == "profile-order":
        entries.reverse()
    elif mutation == "duplicate-profile-identity":
        entries[1] = copy.deepcopy(entries[0])
    elif mutation == "unknown-profile-field":
        _profile(entries[0])["unknown"] = False
    elif mutation == "unknown-taxonomy":
        _profile(entries[0])["asset_purpose"] = "UNKNOWN"
    elif mutation == "profile-renderer-version":
        _profile(entries[0])["renderer_version"] = "1.0.1"
    elif mutation == "recipe-role-mismatch":
        recipe = _profile(entries[0])["reference_asset_recipe"]
        assert type(recipe) is dict
        cast(dict[str, object], recipe)["reference_asset_types"] = ["CHARACTER_IDENTITY_SHEET"]
    elif mutation == "repeated-placeholder":
        sections = _profile(entries[1])["sections"]
        assert type(sections) is list
        section_values = cast(list[dict[str, object]], sections)
        section_values[1]["placeholder"] = section_values[0]["placeholder"]
    elif mutation == "invalid-placeholder":
        sections = _profile(entries[1])["sections"]
        assert type(sections) is list
        cast(list[dict[str, object]], sections)[0]["placeholder"] = "unknown"
    else:  # pragma: no cover - the parametrization is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(VisualPromptProfileSourceError, match="exact catalog contract"):
        _parse_visual_prompt_profile_source_bytes(_canonical_document(value))


def test_stable_reader_accepts_one_bounded_regular_file(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    expected = b"{}\n"
    path.write_bytes(expected)

    assert _read_stable_regular_file(path, max_bytes=len(expected)) == expected


def test_regular_file_classifier_rejects_nonordinary_and_reparse_points() -> None:
    regular = cast(
        os.stat_result,
        SimpleNamespace(st_mode=stat.S_IFREG | stat.S_IRUSR, st_file_attributes=0),
    )
    directory = cast(
        os.stat_result,
        SimpleNamespace(st_mode=stat.S_IFDIR | stat.S_IRUSR, st_file_attributes=0),
    )
    symlink = cast(
        os.stat_result,
        SimpleNamespace(st_mode=stat.S_IFLNK | stat.S_IRUSR, st_file_attributes=0),
    )
    windows_reparse = cast(
        os.stat_result,
        SimpleNamespace(
            st_mode=stat.S_IFREG | stat.S_IRUSR,
            st_file_attributes=0x400,
        ),
    )

    assert _is_regular_non_symlink(regular) is True
    assert _is_regular_non_symlink(directory) is False
    assert _is_regular_non_symlink(symlink) is False
    assert _is_regular_non_symlink(windows_reparse) is False


def test_stable_reader_rejects_a_directory(tmp_path: Path) -> None:
    with pytest.raises(VisualPromptProfileSourceError, match="regular non-symlink"):
        _read_stable_regular_file(tmp_path, max_bytes=4)


def test_stable_reader_rejects_oversize_before_read(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_bytes(b"12345")

    with pytest.raises(VisualPromptProfileSourceError, match="bounded regular"):
        _read_stable_regular_file(path, max_bytes=4)


def test_stable_reader_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"{}\n")
    link = tmp_path / "source.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("this host does not permit an unprivileged file symlink")

    with pytest.raises(VisualPromptProfileSourceError, match="regular non-symlink"):
        _read_stable_regular_file(link, max_bytes=4)


def test_stable_reader_rejects_opened_file_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.json"
    path.write_bytes(b"{}\n")
    original_fstat = os.fstat
    calls = 0

    def drifting_fstat(descriptor: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        info = original_fstat(descriptor)
        if calls == 2:
            return cast(
                os.stat_result,
                SimpleNamespace(
                    st_mode=info.st_mode,
                    st_dev=info.st_dev,
                    st_ino=info.st_ino,
                    st_size=info.st_size + 1,
                    st_mtime_ns=info.st_mtime_ns,
                    st_file_attributes=getattr(info, "st_file_attributes", 0),
                ),
            )
        return info

    monkeypatch.setattr(os, "fstat", drifting_fstat)
    with pytest.raises(VisualPromptProfileSourceError, match="changed identity or size"):
        _read_stable_regular_file(path, max_bytes=4)


def test_stable_reader_rejects_replacement_before_opened_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.json"
    path.write_bytes(b"{}\n")
    original_fstat = os.fstat
    calls = 0

    def replaced_fstat(descriptor: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        info = original_fstat(descriptor)
        if calls == 1:
            return cast(
                os.stat_result,
                SimpleNamespace(
                    st_mode=info.st_mode,
                    st_dev=info.st_dev,
                    st_ino=info.st_ino + 1,
                    st_size=info.st_size,
                    st_mtime_ns=info.st_mtime_ns,
                    st_file_attributes=getattr(info, "st_file_attributes", 0),
                ),
            )
        return info

    monkeypatch.setattr(os, "fstat", replaced_fstat)
    with pytest.raises(VisualPromptProfileSourceError, match="changed before its read"):
        _read_stable_regular_file(path, max_bytes=4)


def test_stable_reader_rejects_named_path_replacement_after_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.json"
    path.write_bytes(b"{}\n")
    original_lstat = Path.lstat
    calls = 0

    def replaced_lstat(candidate: Path) -> os.stat_result:
        nonlocal calls
        info = original_lstat(candidate)
        if candidate == path:
            calls += 1
            if calls == 2:
                return cast(
                    os.stat_result,
                    SimpleNamespace(
                        st_mode=info.st_mode,
                        st_dev=info.st_dev,
                        st_ino=info.st_ino + 1,
                        st_size=info.st_size,
                        st_mtime_ns=info.st_mtime_ns,
                        st_file_attributes=getattr(info, "st_file_attributes", 0),
                    ),
                )
        return info

    monkeypatch.setattr(Path, "lstat", replaced_lstat)
    with pytest.raises(VisualPromptProfileSourceError, match="changed identity or size"):
        _read_stable_regular_file(path, max_bytes=4)


def test_source_mutation_helpers_do_not_modify_committed_source() -> None:
    before = SOURCE_PATH.read_bytes()
    value = copy.deepcopy(_source_value())
    value["source_revision"] = "test-only"

    assert _canonical_document(value) != before
    assert SOURCE_PATH.read_bytes() == before
