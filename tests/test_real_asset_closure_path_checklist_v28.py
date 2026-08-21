from __future__ import annotations

import ast
import glob
import hashlib
import inspect
import json
import os
from dataclasses import FrozenInstanceError, dataclass, replace
from pathlib import Path
from typing import Any, cast

import pytest
from test_real_asset_qualification_preparer_v21 import (
    _canonical_document,
    _make_pack,
)

import sdc.real_asset_closure_path_checklist_v28 as checklist_module
from sdc.real_asset_closure_path_checklist_v28 import (
    TrustedLocalClosurePathChecklistError,
    TrustedLocalClosurePathChecklistV28,
    build_closure_path_checklist_v28,
    main,
)
from sdc.real_asset_intake import CreativeSampleFrozenRealAssetPackManifest

_COMMON_ARGUMENTS = (
    "--pack-root",
    "--evidence",
    "--reviewer-a",
    "--reviewer-b",
    "--pair-check",
    "--evidence-retained-record",
    "--evidence-preparer-ref",
    "--reviewer-a-retained-record",
    "--reviewer-b-retained-record",
    "--qualification-request",
    "--qualifier-ref",
    "--qualification-instruction",
    "--qualification-decision",
    "--rights-manifest-file",
)
_REQUEST_ARGUMENTS = (
    *_COMMON_ARGUMENTS,
    "--use-plan-file",
    "--maker-identity-ref",
    "--maker-input",
)
_INSTRUCTION_ARGUMENTS = (
    *_REQUEST_ARGUMENTS,
    "--checker-identity-ref",
    "--checker-input",
)
_VERIFICATION_ARGUMENTS = (
    *_COMMON_ARGUMENTS,
    "--use-plan-file",
    "--maker-identity-ref",
    "--checker-identity-ref",
    "--review-record-file",
)
_PROFILE_ARGUMENTS = {
    "USE_PLAN_29": _COMMON_ARGUMENTS,
    "REVIEW_REQUEST_32": _REQUEST_ARGUMENTS,
    "REVIEW_INSTRUCTION_34": _INSTRUCTION_ARGUMENTS,
    "REVIEW_RECORD_VERIFICATION_33": _VERIFICATION_ARGUMENTS,
}
_PROFILE_MODULES = {
    "USE_PLAN_29": "sdc.real_asset_use_plan_finalizer_v27",
    "REVIEW_REQUEST_32": "sdc.real_asset_use_scope_review_finalizer_v27",
    "REVIEW_INSTRUCTION_34": "sdc.real_asset_use_scope_review_finalizer_v27",
    "REVIEW_RECORD_VERIFICATION_33": "sdc.real_asset_use_scope_review_finalizer_v27",
}
_ALLOWED_ROWS = (
    ("USE_PLAN_29", "inspect-use-plan-ready", 29),
    ("USE_PLAN_29", "finalize-use-plan", 29),
    ("REVIEW_REQUEST_32", "preflight-review-request", 32),
    ("REVIEW_INSTRUCTION_34", "preflight-review-instruction", 34),
    ("REVIEW_INSTRUCTION_34", "finalize-review-record", 34),
    ("REVIEW_RECORD_VERIFICATION_33", "verify-review-record", 33),
)


@dataclass(frozen=True, slots=True)
class SyntheticChecklistClosure:
    pack: CreativeSampleFrozenRealAssetPackManifest
    pack_root: Path
    manifest_path: Path
    media_paths: tuple[Path, ...]
    explicit_paths: dict[str, Path]


def _write(path: Path, raw: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path.resolve()


@pytest.fixture
def checklist_closure(tmp_path: Path) -> SyntheticChecklistClosure:
    pack, media_bytes = _make_pack()
    pack_root = (tmp_path / pack.pack_id).resolve()
    pack_root.mkdir()
    media_paths = tuple(
        _write(pack_root.joinpath(*descriptor.object_path.split("/")), raw)
        for descriptor, raw in zip(pack.objects, media_bytes, strict=True)
    )
    manifest_path = _write(pack_root / "asset-pack.json", _canonical_document(pack))

    explicit_paths: dict[str, Path] = {"--pack-root": pack_root}
    all_external = tuple(
        dict.fromkeys(
            (
                *_COMMON_ARGUMENTS[1:],
                "--use-plan-file",
                "--maker-identity-ref",
                "--maker-input",
                "--checker-identity-ref",
                "--checker-input",
                "--review-record-file",
            )
        )
    )
    for ordinal, argument in enumerate(all_external):
        suffix = ".json" if argument.endswith(("-file", "-input")) else ".bin"
        explicit_paths[argument] = _write(
            tmp_path / f"external-area-{ordinal:02d}" / f"source{suffix}",
            f"synthetic-checklist-source-{ordinal}:{argument}".encode(),
        )
    return SyntheticChecklistClosure(
        pack=pack,
        pack_root=pack_root,
        manifest_path=manifest_path,
        media_paths=media_paths,
        explicit_paths=explicit_paths,
    )


def _seed_payload(
    closure: SyntheticChecklistClosure,
    *,
    profile: str,
    command: str,
) -> dict[str, object]:
    return {
        "document_type": "sdc.trusted-local-closure-path-checklist-seed",
        "explicit_paths": {
            argument: str(closure.explicit_paths[argument])
            for argument in _PROFILE_ARGUMENTS[profile]
        },
        "profile": profile,
        "schema_version": "1.0.0",
        "target_command": command,
        "target_finalizer_module": _PROFILE_MODULES[profile],
        "target_finalizer_version": "v2.7",
    }


def _seed_file(
    tmp_path: Path,
    payload: dict[str, object],
    *,
    ordinal: int = 0,
    raw: bytes | None = None,
) -> Path:
    if raw is None:
        raw = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    return _write(tmp_path / f"seed-area-{ordinal:03d}" / "seed.json", raw)


def _render(path: Path) -> str:
    rendered = str(path)
    if os.name == "nt":
        rendered = rendered.replace("/", "\\")
        anchor = str(Path(path.anchor)).replace("/", "\\") if path.anchor else ""
        return rendered if rendered == anchor else rendered.rstrip("\\")
    return rendered if rendered == path.anchor else rendered.rstrip("/")


def _expected_entries(
    closure: SyntheticChecklistClosure,
    profile: str,
) -> tuple[dict[str, object], ...]:
    values: list[tuple[str, int, Path, str]] = [
        ("--pack-root", 0, closure.pack_root, "EXPLICIT"),
        ("--pack-manifest", 0, closure.manifest_path, "MANIFEST_DERIVED"),
    ]
    values.extend(
        ("--media-path", occurrence, path, "MANIFEST_DERIVED")
        for occurrence, path in enumerate(closure.media_paths)
    )
    values.extend(
        (argument, 0, closure.explicit_paths[argument], "EXPLICIT")
        for argument in _PROFILE_ARGUMENTS[profile]
        if argument != "--pack-root"
    )
    return tuple(
        {
            "argument_name": argument,
            "occurrence": occurrence,
            "ordinal": ordinal,
            "path": _render(path),
            "source": source,
        }
        for ordinal, (argument, occurrence, path, source) in enumerate(values)
    )


def _independent_path_list_sha256(
    result: TrustedLocalClosurePathChecklistV28,
) -> str:
    envelope = {
        "entries": [entry.payload() for entry in result.entries],
        "entry_count": len(result.entries),
        "profile": result.profile,
        "target_command": result.target_command,
        "target_finalizer_module": result.target_finalizer_module,
        "target_finalizer_version": result.target_finalizer_version,
    }
    raw = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            indent=2,
            separators=(",", ": "),
            sort_keys=True,
        )
        + "\n"
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _compact_line(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def test_public_surface_and_profile_command_matrix_are_exact_and_frozen() -> None:
    assert checklist_module.__all__ == [
        "ClosurePathChecklistEntryV28",
        "TrustedLocalClosurePathChecklistError",
        "TrustedLocalClosurePathChecklistV28",
        "build_closure_path_checklist_v28",
        "main",
    ]
    assert str(inspect.signature(build_closure_path_checklist_v28)) == (
        "(seed_path: 'Path') -> 'TrustedLocalClosurePathChecklistV28'"
    )
    assert str(inspect.signature(main)) == "(argv: 'list[str] | None' = None) -> 'int'"
    assert tuple(checklist_module._PROFILE_SPECS) == tuple(_PROFILE_ARGUMENTS)
    observed_rows = tuple(
        (profile, command, spec.expected_count)
        for profile, spec in checklist_module._PROFILE_SPECS.items()
        for command in spec.commands
    )
    assert observed_rows == _ALLOWED_ROWS
    for profile, spec in checklist_module._PROFILE_SPECS.items():
        assert spec.profile == profile
        assert spec.target_module == _PROFILE_MODULES[profile]
        assert spec.explicit_arguments == _PROFILE_ARGUMENTS[profile]
        with pytest.raises(FrozenInstanceError):
            spec.expected_count = 0  # type: ignore[misc]
    with pytest.raises(TypeError):
        checklist_module._PROFILE_SPECS["USE_PLAN_29"] = object()  # type: ignore[index]


def test_all_profiles_bind_exact_v27_arguments_manifest_order_and_digest(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
) -> None:
    results: dict[tuple[str, str], TrustedLocalClosurePathChecklistV28] = {}
    for ordinal, (profile, command, expected_count) in enumerate(_ALLOWED_ROWS):
        seed = _seed_file(
            tmp_path,
            _seed_payload(checklist_closure, profile=profile, command=command),
            ordinal=ordinal,
        )
        result = build_closure_path_checklist_v28(seed)
        results[(profile, command)] = result
        assert result.profile == profile
        assert result.target_finalizer_module == _PROFILE_MODULES[profile]
        assert result.target_finalizer_version == "v2.7"
        assert result.target_command == command
        assert len(result.entries) == expected_count
        assert [entry.payload() for entry in result.entries] == list(
            _expected_entries(checklist_closure, profile)
        )
        assert result.path_list_sha256 == _independent_path_list_sha256(result)
        assert result.path_format == ("WINDOWS_BACKSLASH" if os.name == "nt" else "POSIX_SLASH")

    assert (
        results[("USE_PLAN_29", "inspect-use-plan-ready")].entries
        == results[("USE_PLAN_29", "finalize-use-plan")].entries
    )
    assert (
        results[("USE_PLAN_29", "inspect-use-plan-ready")].path_list_sha256
        != results[("USE_PLAN_29", "finalize-use-plan")].path_list_sha256
    )
    assert (
        results[("REVIEW_INSTRUCTION_34", "preflight-review-instruction")].entries
        == results[("REVIEW_INSTRUCTION_34", "finalize-review-record")].entries
    )
    assert (
        results[("REVIEW_INSTRUCTION_34", "preflight-review-instruction")].path_list_sha256
        != results[("REVIEW_INSTRUCTION_34", "finalize-review-record")].path_list_sha256
    )
    verification_arguments = tuple(
        entry.argument_name
        for entry in results[("REVIEW_RECORD_VERIFICATION_33", "verify-review-record")].entries[-4:]
    )
    assert verification_arguments == (
        "--use-plan-file",
        "--maker-identity-ref",
        "--checker-identity-ref",
        "--review-record-file",
    )
    assert "--maker-input" not in verification_arguments
    assert "--checker-input" not in verification_arguments


def test_seed_format_key_order_and_path_independent_transport_are_digest_neutral(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
) -> None:
    payload = _seed_payload(
        checklist_closure,
        profile="REVIEW_INSTRUCTION_34",
        command="preflight-review-instruction",
    )
    lf_raw = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    crlf_raw = lf_raw.replace(b"\n", b"\r\n")
    reversed_payload = dict(reversed(tuple(payload.items())))
    explicit = cast(dict[str, str], reversed_payload["explicit_paths"])
    reversed_payload["explicit_paths"] = dict(reversed(tuple(explicit.items())))
    reordered_raw = (json.dumps(reversed_payload, ensure_ascii=False) + "\n").encode()
    seeds = (
        _seed_file(tmp_path, payload, ordinal=10, raw=lf_raw),
        _seed_file(tmp_path, payload, ordinal=11, raw=crlf_raw),
        _seed_file(tmp_path, payload, ordinal=12, raw=reordered_raw),
    )
    results = tuple(build_closure_path_checklist_v28(seed) for seed in seeds)
    assert results[0] == results[1] == results[2]
    assert all(
        str(seed) not in json.dumps(result.payload())
        for seed, result in zip(seeds, results, strict=True)
    )


def test_hostile_seed_shapes_and_profile_inapplicable_paths_fail_closed(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
) -> None:
    valid = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    invalid_payloads: list[dict[str, object]] = []

    unknown = {**valid, "unexpected": "synthetic"}
    invalid_payloads.append(unknown)
    missing = dict(valid)
    del missing["target_command"]
    invalid_payloads.append(missing)
    wrong_module = {**valid, "target_finalizer_module": "sdc.unknown_finalizer_v99"}
    invalid_payloads.append(wrong_module)
    wrong_version = {**valid, "target_finalizer_version": "v2.8"}
    invalid_payloads.append(wrong_version)
    wrong_command = {**valid, "target_command": "verify-use-plan"}
    invalid_payloads.append(wrong_command)
    wrong_profile = {**valid, "profile": "UNKNOWN_29"}
    invalid_payloads.append(wrong_profile)
    coerced = json.loads(json.dumps(valid))
    coerced["explicit_paths"]["--evidence"] = 7
    invalid_payloads.append(coerced)
    null_path = json.loads(json.dumps(valid))
    null_path["explicit_paths"]["--evidence"] = None
    invalid_payloads.append(null_path)
    missing_path = json.loads(json.dumps(valid))
    del missing_path["explicit_paths"]["--evidence"]
    invalid_payloads.append(missing_path)
    derived_override = json.loads(json.dumps(valid))
    derived_override["explicit_paths"]["--media-path"] = str(checklist_closure.media_paths[0])
    invalid_payloads.append(derived_override)
    inapplicable = json.loads(json.dumps(valid))
    inapplicable["explicit_paths"]["--use-plan-file"] = str(
        checklist_closure.explicit_paths["--use-plan-file"]
    )
    invalid_payloads.append(inapplicable)

    for ordinal, payload in enumerate(invalid_payloads, start=20):
        with pytest.raises(TrustedLocalClosurePathChecklistError):
            build_closure_path_checklist_v28(_seed_file(tmp_path, payload, ordinal=ordinal))

    duplicate_raw = json.dumps(valid, ensure_ascii=False)[:-1] + ',"profile":"USE_PLAN_29"}'
    invalid_raw = (
        b"",
        b"\xef\xbb\xbf" + json.dumps(valid).encode(),
        b"\xff\xfe",
        b'{"value":NaN}',
        duplicate_raw.encode(),
        b" " * (64 * 1024 + 1),
    )
    for ordinal, raw in enumerate(invalid_raw, start=40):
        with pytest.raises(TrustedLocalClosurePathChecklistError):
            build_closure_path_checklist_v28(_seed_file(tmp_path, valid, ordinal=ordinal, raw=raw))


def test_wrong_profile_command_pairs_fail_before_path_materialization(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(seed: object) -> None:
        del seed
        raise AssertionError("path materialization must not run")

    monkeypatch.setattr(checklist_module, "_materialize_entries", forbidden)
    rejected = (
        ("USE_PLAN_29", "verify-use-plan"),
        ("REVIEW_REQUEST_32", "finalize-review-record"),
        ("REVIEW_INSTRUCTION_34", "preflight-review-request"),
        ("REVIEW_RECORD_VERIFICATION_33", "preflight-review-instruction"),
    )
    for ordinal, (profile, command) in enumerate(rejected, start=60):
        seed = _seed_file(
            tmp_path,
            _seed_payload(checklist_closure, profile=profile, command=command),
            ordinal=ordinal,
        )
        with pytest.raises(TrustedLocalClosurePathChecklistError):
            build_closure_path_checklist_v28(seed)


def test_manifest_derivation_does_not_scan_sort_or_interpret_media_bytes(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    seed = _seed_file(tmp_path, payload, ordinal=70)
    baseline = build_closure_path_checklist_v28(seed)
    first_media = checklist_closure.media_paths[0]
    original_media = first_media.read_bytes()
    first_media.write_bytes(bytes([original_media[0] ^ 0xFF]) + original_media[1:])
    (checklist_closure.pack_root / "synthetic-decoy.bin").write_bytes(b"not discovered")

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("directory discovery is forbidden")

    monkeypatch.setattr(Path, "glob", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    monkeypatch.setattr(Path, "iterdir", forbidden)
    monkeypatch.setattr(glob, "glob", forbidden)
    monkeypatch.setattr(glob, "iglob", forbidden)
    monkeypatch.setattr(os, "listdir", forbidden)
    monkeypatch.setattr(os, "scandir", forbidden)
    monkeypatch.setattr(os, "walk", forbidden)
    result = build_closure_path_checklist_v28(seed)
    assert result.entries == baseline.entries
    assert result.path_list_sha256 == baseline.path_list_sha256
    assert tuple(entry.path for entry in result.entries[2:16]) == tuple(
        _render(path) for path in checklist_closure.media_paths
    )


@pytest.mark.parametrize("mutation", ("reordered", "missing", "extra", "absolute", "traversal"))
def test_malformed_or_reordered_manifest_objects_fail_closed(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    mutation: str,
) -> None:
    manifest = json.loads(checklist_closure.manifest_path.read_bytes())
    objects = manifest["objects"]
    if mutation == "reordered":
        manifest["objects"] = list(reversed(objects))
    elif mutation == "missing":
        manifest["objects"] = objects[:-1]
    elif mutation == "extra":
        manifest["objects"] = [*objects, objects[-1]]
    elif mutation == "absolute":
        objects[0]["object_path"] = "C:/synthetic/escape.bin"
    else:
        objects[0]["object_path"] = "objects/../escape.bin"
    checklist_closure.manifest_path.write_bytes(
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    )
    seed = _seed_file(
        tmp_path,
        _seed_payload(
            checklist_closure,
            profile="USE_PLAN_29",
            command="inspect-use-plan-ready",
        ),
        ordinal=80,
    )
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(seed)


def test_relative_missing_wrong_kind_pack_overlap_and_mutable_alias_paths_fail(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
) -> None:
    base = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    missing = tmp_path / "absent-area" / "absent.bin"
    directory = (tmp_path / "ordinary-directory").resolve()
    directory.mkdir()
    inside_pack = _write(
        checklist_closure.pack_root / "synthetic-external.bin",
        b"synthetic pack overlap",
    )
    mutable = _write(tmp_path / "latest" / "source.bin", b"synthetic mutable alias")
    rejected_values = (
        "relative/source.bin",
        str(missing),
        str(directory),
        str(inside_pack),
        str(mutable),
        r"\\server\share\source.bin",
        r"\\.\C:\source.bin",
    )
    for ordinal, value in enumerate(rejected_values, start=90):
        payload = json.loads(json.dumps(base))
        payload["explicit_paths"]["--evidence"] = value
        with pytest.raises(TrustedLocalClosurePathChecklistError):
            build_closure_path_checklist_v28(_seed_file(tmp_path, payload, ordinal=ordinal))

    overlapping_decision = _write(
        checklist_closure.explicit_paths["--qualification-request"].parent
        / "synthetic-decision.bin",
        b"synthetic overlapping trust area",
    )
    payload = json.loads(json.dumps(base))
    payload["explicit_paths"]["--qualification-decision"] = str(overlapping_decision)
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(_seed_file(tmp_path, payload, ordinal=99))


def test_duplicate_casefold_alias_and_physical_aliases_fail_closed(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    duplicate = json.loads(json.dumps(base))
    duplicate["explicit_paths"]["--reviewer-b"] = duplicate["explicit_paths"]["--reviewer-a"]
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(_seed_file(tmp_path, duplicate, ordinal=100))

    original_seal = checklist_module._regular_file_seal

    def case_alias(path: Path, *, field: str) -> object:
        seal = original_seal(path, field=field)
        if field == "--reviewer-a":
            return replace(seal, path=Path("C:/Synthetic/CaseAlias.json"))
        if field == "--reviewer-b":
            return replace(seal, path=Path("c:/synthetic/casealias.JSON"))
        return seal

    monkeypatch.setattr(checklist_module, "_regular_file_seal", case_alias)
    with pytest.raises(TrustedLocalClosurePathChecklistError, match="path alias"):
        build_closure_path_checklist_v28(_seed_file(tmp_path, base, ordinal=101))


def test_hardlinked_seed_and_source_fail_closed_when_supported(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
) -> None:
    payload = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    seed = _seed_file(tmp_path, payload, ordinal=110)
    seed_link = tmp_path / "seed-hardlink.json"
    try:
        os.link(seed, seed_link)
    except OSError:
        pytest.skip("hard links are unavailable on this host")
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(seed)
    seed_link.unlink()

    source = checklist_closure.explicit_paths["--evidence"]
    source_link = tmp_path / "source-hardlink.bin"
    os.link(source, source_link)
    seed = _seed_file(tmp_path, payload, ordinal=111)
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(seed)


def test_symbolic_link_and_mocked_reparse_directory_fail_closed_when_supported(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = checklist_closure.explicit_paths["--evidence"]
    symbolic_path = tmp_path / "symbolic-area" / "source.bin"
    symbolic_path.parent.mkdir()
    try:
        symbolic_path.symlink_to(target)
    except OSError:
        symbolic: Path | None = None
    else:
        symbolic = symbolic_path
    if symbolic is not None:
        payload = _seed_payload(
            checklist_closure,
            profile="USE_PLAN_29",
            command="inspect-use-plan-ready",
        )
        cast(dict[str, str], payload["explicit_paths"])["--evidence"] = str(symbolic)
        with pytest.raises(TrustedLocalClosurePathChecklistError):
            build_closure_path_checklist_v28(_seed_file(tmp_path, payload, ordinal=120))

    class ReparseDirectory:
        pass

    probe = ReparseDirectory()
    path_boundary = cast(Any, checklist_module)._path_boundary
    monkeypatch.setattr(
        path_boundary,
        "_safe_absolute",
        lambda path, must_exist, field: path,
    )

    def reject_reparse(path: object, *, field: str) -> None:
        del path, field
        raise path_boundary.TrustedLocalRightsManifestFinalizationError("synthetic reparse point")

    monkeypatch.setattr(path_boundary, "_directory_identity", reject_reparse)
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        checklist_module._directory_seal(
            cast(Path, probe),
            field="synthetic reparse directory",
        )


@pytest.mark.parametrize("drift", ("seed", "manifest", "source", "link-count"))
def test_each_post_materialization_toctou_drift_fails_closed(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    payload = _seed_payload(
        checklist_closure,
        profile="USE_PLAN_29",
        command="inspect-use-plan-ready",
    )
    seed = _seed_file(tmp_path, payload, ordinal=130)
    original_materialize = checklist_module._materialize_entries
    replacement = _write(
        checklist_closure.explicit_paths["--evidence"].with_name("replacement.bin"),
        b"synthetic replacement with a different physical identity",
    )
    if drift == "link-count":
        probe = tmp_path / "hardlink-probe.bin"
        try:
            os.link(checklist_closure.explicit_paths["--evidence"], probe)
        except OSError:
            pytest.skip("hard links are unavailable on this host")
        probe.unlink()

    def materialize(value: object) -> object:
        result = original_materialize(value)  # type: ignore[arg-type]
        if drift == "seed":
            seed.write_bytes(seed.read_bytes() + b" ")
        elif drift == "manifest":
            checklist_closure.manifest_path.write_bytes(
                checklist_closure.manifest_path.read_bytes() + b" "
            )
        elif drift == "source":
            os.replace(replacement, checklist_closure.explicit_paths["--evidence"])
        else:
            os.link(
                checklist_closure.explicit_paths["--evidence"],
                tmp_path / "post-capture-hardlink.bin",
            )
        return result

    monkeypatch.setattr(checklist_module, "_materialize_entries", materialize)
    with pytest.raises(TrustedLocalClosurePathChecklistError):
        build_closure_path_checklist_v28(seed)


def test_capture_sequence_is_seed_manifest_then_exact_replay(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _seed_file(
        tmp_path,
        _seed_payload(
            checklist_closure,
            profile="USE_PLAN_29",
            command="inspect-use-plan-ready",
        ),
        ordinal=140,
    )
    events: list[str] = []
    original_read = checklist_module._read_bounded_file
    original_materialize = checklist_module._materialize_entries

    def read(path: Path, *, maximum_bytes: int, field: str) -> object:
        events.append(f"read:{field}")
        return original_read(path, maximum_bytes=maximum_bytes, field=field)

    def materialize(value: object) -> object:
        events.append("materialize:start")
        result = original_materialize(value)  # type: ignore[arg-type]
        events.append("materialize:end")
        return result

    monkeypatch.setattr(checklist_module, "_read_bounded_file", read)
    monkeypatch.setattr(checklist_module, "_materialize_entries", materialize)
    build_closure_path_checklist_v28(seed)
    assert events == [
        "read:checklist seed",
        "materialize:start",
        "read:frozen Pack manifest",
        "materialize:end",
        "read:checklist seed",
        "read:frozen Pack manifest",
    ]


def test_windows_and_posix_rendering_is_stable_without_case_rewriting() -> None:
    class RenderProbe:
        def __init__(self, rendered: str, anchor: str) -> None:
            self.rendered = rendered
            self.anchor = anchor

        def __str__(self) -> str:
            return self.rendered

    windows_path = cast(Path, RenderProbe("C:/Synthetic/MiXeD/", "C:\\"))
    windows_root = cast(Path, RenderProbe("C:\\", "C:\\"))
    posix_path = cast(Path, RenderProbe("/Synthetic/MiXeD/", "/"))
    posix_root = cast(Path, RenderProbe("/", "/"))
    assert checklist_module._render_admitted_path(windows_path, windows=True) == (
        "C:\\Synthetic\\MiXeD"
    )
    assert checklist_module._render_admitted_path(windows_root, windows=True) == "C:\\"
    assert checklist_module._render_admitted_path(posix_path, windows=False) == ("/Synthetic/MiXeD")
    assert checklist_module._render_admitted_path(posix_root, windows=False) == "/"


def test_cli_success_is_exact_one_line_manual_only_json_and_writes_no_file(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    seed = _seed_file(
        tmp_path,
        _seed_payload(
            checklist_closure,
            profile="REVIEW_REQUEST_32",
            command="preflight-review-request",
        ),
        ordinal=150,
    )

    def file_state() -> dict[str, tuple[int, int, bytes]]:
        return {
            path.relative_to(tmp_path).as_posix(): (
                path.stat().st_mode,
                path.stat().st_mtime_ns,
                path.read_bytes(),
            )
            for path in tmp_path.rglob("*")
            if path.is_file()
        }

    before = file_state()
    assert main(["render-checklist", "--seed", str(seed)]) == 0
    assert file_state() == before
    captured = capfdbinary.readouterr()
    assert captured.err == b""
    payload = json.loads(captured.out)
    assert captured.out == _compact_line(payload)
    assert set(payload) == {
        "automated_execution_allowed",
        "current_gate",
        "document_type",
        "entries",
        "entry_count",
        "execution_authorized",
        "generator_version",
        "manual_confirmation_required",
        "path_format",
        "path_list_sha256",
        "posts_allowed",
        "profile",
        "provider_requests",
        "provider_state",
        "schema_version",
        "status",
        "target_command",
        "target_finalizer_module",
        "target_finalizer_version",
        "usage_restriction",
    }
    assert payload["status"] == "PATH_CHECKLIST_READY_FOR_HUMAN_REVIEW_ONLY"
    assert payload["usage_restriction"] == ("MANUAL_REVIEW_ONLY_NOT_FOR_AUTOMATED_EXECUTION")
    assert payload["automated_execution_allowed"] is False
    assert payload["manual_confirmation_required"] is True
    assert payload["execution_authorized"] is False
    assert payload["current_gate"] == "HUMAN_GATE"
    assert payload["provider_state"] == "NOT_AUTHORIZED"
    assert payload["provider_requests"] == payload["posts_allowed"] == 0
    rendered = captured.out.decode().casefold()
    for forbidden in (
        '"argv"',
        '"shell_command"',
        '"output"',
        '"seed"',
        '"generated_at"',
        '"observed_at"',
        '"credentials"',
    ):
        assert forbidden not in rendered


def test_cli_failures_are_generic_bounded_and_never_echo_private_paths(
    checklist_closure: SyntheticChecklistClosure,
    tmp_path: Path,
    capfdbinary: pytest.CaptureFixture[bytes],
) -> None:
    seed = _seed_file(
        tmp_path,
        _seed_payload(
            checklist_closure,
            profile="USE_PLAN_29",
            command="inspect-use-plan-ready",
        ),
        ordinal=160,
    )
    rejected = (
        ["--help"],
        ["render", "--seed", str(seed)],
        ["render-checklist", "--see", str(seed)],
        ["render-checklist", "--seed", str(seed), "--seed", str(seed)],
        ["render-checklist", "--seed", str(seed), "--output", str(tmp_path / "out.json")],
        ["render-checklist", "--seed", str(tmp_path / "private-missing-seed.json")],
    )
    for argv in rejected:
        assert main(argv) == 2
        captured = capfdbinary.readouterr()
        assert captured.out == b""
        assert captured.err == b'{"error":"FAILED_CLOSED"}\n'
        assert str(seed).encode() not in captured.err
        assert str(tmp_path).encode() not in captured.err


def test_ast_and_runtime_surface_prohibit_discovery_clock_network_and_execution() -> None:
    source = inspect.getsource(checklist_module)
    tree = ast.parse(source)
    for token in (
        ".glob(",
        ".rglob(",
        ".iterdir(",
        "glob.glob(",
        "glob.iglob(",
        "os.listdir(",
        "os.scandir(",
        "os.walk(",
        "datetime.now(",
        "datetime.utcnow(",
        "time.time(",
        "requests.",
        "httpx.",
        "socket.",
        "subprocess.",
        "inspect_use_plan_ready(",
        "finalize_use_plan(",
        "preflight_review_request(",
        "preflight_review_instruction(",
        "finalize_review_record(",
        "verify_review_record(",
        "O_WRONLY",
        "O_RDWR",
        "O_CREAT",
        "O_TRUNC",
    ):
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
    assert commands == {"render-checklist"}
    forbidden_import_fragments = {
        "authorization",
        "entitlement",
        "ledger",
        "network",
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
