"""Fixed repository-only known answers for the accepted ADR-045 boundary.

The CLI has exactly two explicit modes. It reads one frozen human-reviewed source
packet and the complete frozen set of sixteen earlier visual-prompt fixtures, then
either checks or directly rewrites one derived JSON fixture. It performs no Provider,
network, credential, clock, Runtime, publication, role-binding, asset-use or recursive
discovery work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tomllib
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Never, cast

from pydantic import BaseModel, ValidationError

from sdc import generated_reference_asset_promotion as promotion_module
from sdc import generated_reference_candidate as candidate_module
from sdc import generated_reference_candidate_codegen as candidate_codegen
from sdc import generated_reference_rights_current_status as rights_module
from sdc import generated_reference_rights_current_status_codegen as rights_codegen
from sdc.contracts import CharacterAssetVersion, CharacterBible, SceneAssetVersion, SceneBible
from sdc.visual_reference_prompt_compiler import CreativeSampleReferenceVisualPromptArtifactV1

_KNOWN_ANSWER_VERSION = "1.0.0"
_FIXTURE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated-reference-asset-promotion"
_REVIEWED_SOURCE_PATH = f"{_FIXTURE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_DERIVED_FIXTURE_PATH = f"{_FIXTURE_DIRECTORY}/generated-known-answer-v1.json"

_CANDIDATE_DIRECTORY = "tests/fixtures/visual_prompt_profiles/generated-reference-candidate"
_CANDIDATE_SOURCE_PATH = f"{_CANDIDATE_DIRECTORY}/reviewed-known-answer-source-v1.json"
_CANDIDATE_GENERATED_PATH = f"{_CANDIDATE_DIRECTORY}/generated-known-answer-v1.json"
_CHARACTER_PNG_PATH = f"{_CANDIDATE_DIRECTORY}/character-reference-synthetic-v1.png"
_SCENE_PNG_PATH = f"{_CANDIDATE_DIRECTORY}/scene-reference-synthetic-v1.png"
_RIGHTS_DIRECTORY = (
    "tests/fixtures/visual_prompt_profiles/generated-reference-rights-current-status"
)
_RIGHTS_SOURCE_PATH = f"{_RIGHTS_DIRECTORY}/reviewed-known-answer-source-v1.json"
_RIGHTS_GENERATED_PATH = f"{_RIGHTS_DIRECTORY}/generated-known-answer-v1.json"
_PRIMARY_ASSET_SOURCE_PATH = (
    "tests/fixtures/visual_prompt_profiles/reference-compiler/"
    "reviewed-known-answer-source-v1.json"
)

# The old-fixture map is intentionally complete. It is not a discovery result and it is not
# narrowed to the subset needed by the two positive cases. The reviewed ADR-045 source anchor
# is added only after its separate byte review; the sentinel makes both CLI modes fail closed
# until that review has happened.
_FROZEN_OLD_FIXTURE_FINGERPRINTS: dict[str, tuple[int, str]] = {
    "tests/fixtures/visual_prompt_profiles/compiler-integration/reviewed-known-answer-v1.json": (
        26_163,
        "40b42f406f76fef0a07f1a810d7ff4853f7f765edd48e8e998d1504fdfc0336e",
    ),
    _CHARACTER_PNG_PATH: (
        5_841,
        "3c20c94c18fbd72b68a58748bae9aba2daefc6baa38e9fc1c6ab30b40e6f39fc",
    ),
    _CANDIDATE_GENERATED_PATH: (
        84_090,
        "aaaf5fed96b2e867a99debf9ddfcc2759febd6e87ccb7defef3e4ae5f0b120a3",
    ),
    _CANDIDATE_SOURCE_PATH: (
        101_487,
        "b385164d9dabd467308250da41166e1a0d47b8cf8504eb15b5644590aa9edb55",
    ),
    _SCENE_PNG_PATH: (
        5_754,
        "97019f80b032242f33963836ce661e8761add311cdc7f8bd7b63ac247c0e5574",
    ),
    _RIGHTS_GENERATED_PATH: (
        294_275,
        "f043c46eabddd07fb8a18c73fca267f8e523e29da8aebb7df95a7e98ae196c75",
    ),
    _RIGHTS_SOURCE_PATH: (
        46_739,
        "d6c74ecb90c4c14abe47dbbd3d4ecd8fff8d5a4e0e90dbb2edae166773160315",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "character-reference-basic.prompt-render-receipt.json"
    ): (
        1_452,
        "2510e83345bc930d219e112b4c4e21834f98876cb205170d452cfedfa1e7f480",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/character-reference-basic.prompt.txt": (
        2_552,
        "7652c02a6abba5d7bf4fc85d296d70c23328dc98913c89bfcaf98f948f54fd87",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "narrative-shot-unicode.prompt-render-receipt.json"
    ): (
        1_447,
        "dda168d064a9c5e1ed2ed6992854bed550d2745a7c594f3cad695937dd419b55",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/narrative-shot-unicode.prompt.txt": (
        1_913,
        "3cf46430509bfe46c36d88b48133fba477d147bf536f58110ec8ffd1adcab5c4",
    ),
    (
        "tests/fixtures/visual_prompt_profiles/generated/"
        "scene-reference-basic.prompt-render-receipt.json"
    ): (
        1_448,
        "d4a5aa90b9f62718ffae6dd9f687f69b109039828608149b7c3945dfccdac93f",
    ),
    "tests/fixtures/visual_prompt_profiles/generated/scene-reference-basic.prompt.txt": (
        2_232,
        "fb60a6daabd7b587a0c2759de254fd3812a3fa029a45767956c65e9f9ca838a9",
    ),
    "tests/fixtures/visual_prompt_profiles/reference-compiler/generated-known-answer-v1.json": (
        51_645,
        "0311fdf4ec54a36b3a3b3895c32dd7bbe453fdbbbde37de67db22d9c914b59a8",
    ),
    _PRIMARY_ASSET_SOURCE_PATH: (
        14_587,
        "be072fe5be5ef4b35c2e482db3e60c14641bce8cf80eb95398d9a4468750170c",
    ),
    "tests/fixtures/visual_prompt_profiles/reviewed-known-answer-v1.json": (
        17_678,
        "0b736f1759fc23e4e809f278f978843099cbe98b24e3a4a9359de5274b39ae75",
    ),
}

_REVIEWED_SOURCE_FINGERPRINT = (
    68555,
    "633483d40e8404b2bbe9fc3fa370993b0e6b94148e61507d15962811957257ba",
)
_PROTECTED_FINGERPRINTS: dict[str, tuple[int, str]] = {
    _REVIEWED_SOURCE_PATH: _REVIEWED_SOURCE_FINGERPRINT,
    **_FROZEN_OLD_FIXTURE_FINGERPRINTS,
}

_MAX_SOURCE_BYTES = 2_097_152
_MAX_DERIVED_BYTES = 4_194_304
_MAX_OLD_FIXTURE_BYTES = 4_194_304
_MAX_PNG_BYTES = 67_108_864
_MAX_REPOSITORY_METADATA_BYTES = 262_144
_MAX_JSON_CONTAINER_DEPTH = 24
_MAX_JSON_CONTAINER_ITEMS = 256
_WINDOWS_REPARSE_POINT_ATTRIBUTE = 0x400
_UTF8_BOM = b"\xef\xbb\xbf"

_ROOT_KEYS = ("cases", "known_answer_version", "source_packet_scope")
_CASE_IDS = (
    "character-same-status-record-v1",
    "scene-successor-reconciliation-v1",
)
_PRIMARY_ASSET_CASE_IDS = {
    _CASE_IDS[0]: "character-reference-basic",
    _CASE_IDS[1]: "scene-reference-basic-empty-props",
}

_StatusReceipt = (
    rights_module.CreativeSampleGeneratedReferenceCurrentStatusRecordAsOfAssessmentReceiptV1
)
_process_status_record_as_of = (
    rights_module.process_generated_reference_current_status_record_as_of_assessment
)


class GeneratedReferenceAssetPromotionCodegenError(ValueError):
    """The fixed ADR-045 closure is missing, stale, unsafe or invalid."""


def _fail(message: str) -> Never:
    raise GeneratedReferenceAssetPromotionCodegenError(message)


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    left_identity = (getattr(left, "st_dev", None), getattr(left, "st_ino", None))
    right_identity = (getattr(right, "st_dev", None), getattr(right, "st_ino", None))
    return left_identity == right_identity and left_identity != (None, None)


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


@dataclass(frozen=True, slots=True)
class _WindowsHandleSnapshot:
    identity: tuple[int, int]
    attributes: int
    link_count: int
    size_bytes: int


if sys.platform == "win32":
    import ctypes as _windows_ctypes
    import msvcrt as _windows_msvcrt
    from ctypes import wintypes as _windows_wintypes

    class _WindowsFileId128(_windows_ctypes.Structure):
        _fields_ = (("identifier", _windows_ctypes.c_ubyte * 16),)

    class _WindowsFileIdInfo(_windows_ctypes.Structure):
        _fields_ = (
            ("volume_serial_number", _windows_ctypes.c_ulonglong),
            ("file_id", _WindowsFileId128),
        )

    class _WindowsFileTime(_windows_ctypes.Structure):
        _fields_ = (
            ("low_date_time", _windows_wintypes.DWORD),
            ("high_date_time", _windows_wintypes.DWORD),
        )

    class _WindowsByHandleFileInformation(_windows_ctypes.Structure):
        _fields_ = (
            ("file_attributes", _windows_wintypes.DWORD),
            ("creation_time", _WindowsFileTime),
            ("last_access_time", _WindowsFileTime),
            ("last_write_time", _WindowsFileTime),
            ("volume_serial_number", _windows_wintypes.DWORD),
            ("file_size_high", _windows_wintypes.DWORD),
            ("file_size_low", _windows_wintypes.DWORD),
            ("number_of_links", _windows_wintypes.DWORD),
            ("file_index_high", _windows_wintypes.DWORD),
            ("file_index_low", _windows_wintypes.DWORD),
        )

    def _windows_handle_snapshot(handle: int) -> _WindowsHandleSnapshot:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        get_identity = kernel32.GetFileInformationByHandleEx
        get_identity.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.c_int,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
        )
        get_identity.restype = _windows_wintypes.BOOL
        identity = _WindowsFileIdInfo()
        if not get_identity(
            handle,
            18,
            _windows_ctypes.byref(identity),
            _windows_ctypes.sizeof(identity),
        ):
            raise OSError(
                _windows_ctypes.get_last_error(),
                "GetFileInformationByHandleEx(FileIdInfo) failed",
            )
        get_information = kernel32.GetFileInformationByHandle
        get_information.argtypes = (
            _windows_wintypes.HANDLE,
            _windows_ctypes.POINTER(_WindowsByHandleFileInformation),
        )
        get_information.restype = _windows_wintypes.BOOL
        information = _WindowsByHandleFileInformation()
        if not get_information(handle, _windows_ctypes.byref(information)):
            raise OSError(
                _windows_ctypes.get_last_error(),
                "GetFileInformationByHandle failed",
            )
        return _WindowsHandleSnapshot(
            identity=(
                int(identity.volume_serial_number),
                int.from_bytes(bytes(identity.file_id.identifier), "little"),
            ),
            attributes=int(information.file_attributes),
            link_count=int(information.number_of_links),
            size_bytes=(int(information.file_size_high) << 32)
            | int(information.file_size_low),
        )

    def _close_windows_handle(handle: int) -> None:
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (_windows_wintypes.HANDLE,)
        close_handle.restype = _windows_wintypes.BOOL
        if not close_handle(handle):
            raise OSError(_windows_ctypes.get_last_error(), "CloseHandle failed")

    def _acquire_windows_directory_guard(path: Path) -> int:
        try:
            before = os.lstat(path)
        except OSError as exc:
            raise GeneratedReferenceAssetPromotionCodegenError(
                "anchored Windows directory is missing or inaccessible"
            ) from exc
        if not _is_directory_non_symlink(before):
            _fail("anchored Windows directory must not be a ReparsePoint or symlink")
        kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            _windows_wintypes.LPCWSTR,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.LPVOID,
            _windows_wintypes.DWORD,
            _windows_wintypes.DWORD,
            _windows_wintypes.HANDLE,
        )
        create_file.restype = _windows_wintypes.HANDLE
        handle = create_file(
            str(path),
            0x00000080,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        invalid = _windows_ctypes.c_void_p(-1).value
        if handle == invalid:
            raise GeneratedReferenceAssetPromotionCodegenError(
                "anchored Windows directory handle could not be acquired"
            )
        raw_handle = int(handle)
        try:
            opened = _windows_handle_snapshot(raw_handle)
            after = os.lstat(path)
            expected_identity = (before.st_dev, before.st_ino)
            if (
                bool(opened.attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
                or not bool(opened.attributes & 0x10)
                or opened.identity != expected_identity
                or not _is_directory_non_symlink(after)
                or (after.st_dev, after.st_ino) != opened.identity
            ):
                _fail("anchored Windows directory changed or resolved through a ReparsePoint")
            return raw_handle
        except BaseException:
            _close_windows_handle(raw_handle)
            raise

else:

    def _windows_handle_snapshot(handle: int) -> _WindowsHandleSnapshot:
        del handle
        _fail("Windows handle inspection is unavailable on this host")

    def _close_windows_handle(handle: int) -> None:
        del handle
        _fail("Windows handle closing is unavailable on this host")

    def _acquire_windows_directory_guard(path: Path) -> int:
        del path
        _fail("Windows directory guards are unavailable on this host")


def _read_stable_regular_file(path: Path, *, max_bytes: int, label: str) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        _fail(f"{label} has an invalid byte boundary")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} is missing or inaccessible"
        ) from exc
    if not _is_regular_non_symlink(before) or before.st_nlink != 1:
        _fail(f"{label} must be one regular non-symlink file with one link")
    if not 1 <= before.st_size <= max_bytes:
        _fail(f"{label} exceeds its frozen byte boundary")
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
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not _is_regular_non_symlink(opened) or opened.st_nlink != 1:
            _fail(f"opened {label} is not one regular file")
        if not _same_file(before, opened):
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
                _fail(f"{label} exceeds its frozen byte boundary")
        after_handle = os.fstat(descriptor)
    except GeneratedReferenceAssetPromotionCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} could not be read safely"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} could not be re-inspected"
        ) from exc
    raw = b"".join(chunks)
    if (
        not _is_regular_non_symlink(after_path)
        or after_path.st_nlink != 1
        or _file_identity(before) != _file_identity(after_handle)
        or _file_identity(before) != _file_identity(after_path)
    ):
        _fail(f"{label} changed while it was read")
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
        list_items = cast(list[object], value)
        if len(list_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON array exceeds the frozen item boundary")
        for item in list_items:
            _validate_json_value(
                item,
                depth=depth + 1 if type(item) in {dict, list} else depth,
            )
        return
    if type(value) is dict:
        dict_items = cast(dict[object, object], value)
        if len(dict_items) > _MAX_JSON_CONTAINER_ITEMS:
            _fail("persistent JSON object exceeds the frozen field boundary")
        for key, item in dict_items.items():
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
        raise GeneratedReferenceAssetPromotionCodegenError(
            "persistent JSON serialization failed"
        ) from exc


def _compact_json(value: object) -> bytes:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "compact canonical JSON serialization failed"
        ) from exc


_REVIEW_PAYLOAD_DOMAIN = b"sdc:generated-reference-asset-promotion-review-payload:v1\0"
_PRIMARY_ASSET_VERSION_DOMAIN = (
    b"sdc:generated-reference-primary-asset-version-projection:v1\0"
)
_PRIMARY_BINDING_DOMAIN = b"sdc:generated-reference-primary-asset-binding:v1\0"
_REQUEST_DOMAIN = b"sdc:generated-reference-asset-promotion-request:v1\0"
_DECISION_DOMAIN = b"sdc:generated-reference-asset-promotion-decision:v1\0"
_SIDECAR_DOMAIN = b"sdc:generated-reference-eligible-asset-sidecar:v1\0"

_ZERO_AUTHORITY_FIELDS = (
    "authority_scope",
    "current_gate",
    "provider_state",
    "generation_authorized",
    "execution_authorized",
    "publication_authorized",
    "remote_processing_allowed",
    "retention_allowed",
    "training_allowed",
    "publication_allowed",
    "automated_execution_allowed",
    "authorized_attempts",
    "authorized_cost_cny",
    "posts_allowed",
    "provider_requests",
    "grants_rights",
    "grants_qualification",
    "grants_execution_authority",
    "eligible_for_asset_promotion",
    "replaces_rights_manifest",
    "usage_restriction",
)

_REQUEST_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "request_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "promotion_review_payload_sha256",
    "reference_prompt_artifact_sha256",
    "provider_attempt_outcome_id",
    "provider_attempt_outcome_sha256",
    "candidate_id",
    "candidate_sha256",
    "output_ordinal",
    "media_type",
    "media_content_sha256",
    "media_size_bytes",
    "media_technical_record_sha256",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_decision_at",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_at",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "requested_status_record_id",
    "requested_status_record_sha256",
    "requested_status_receipt_id",
    "requested_status_receipt_sha256",
    "requested_explicit_chain_set_sha256",
    "requested_coverage_set_sha256",
    "requested_joint_replay_sha256",
    "requested_as_of_assessment_sha256",
    "requested_as_of",
    "requested_as_of_status",
    "requested_status_valid_until",
    "requested_primary_asset_binding",
    "maker_identity_ref_sha256",
    "maker_action_sha256",
    "maker_prepared_at",
    "requested_at",
    "request_valid_until",
    "request_basis",
    "requested_representation",
    "composite_media_unsplit",
    "role_assignment_embedded",
    "bible_mutation_requested",
    "provider_input_requested",
    "promotion_performed",
    "sidecar_materialized",
    "eligible_for_separate_role_binding_review",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_FIELDS,
)

_DECISION_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "decision_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "promotion_review_payload_sha256",
    "request_id",
    "request_sha256",
    "reference_prompt_artifact_sha256",
    "provider_attempt_outcome_id",
    "provider_attempt_outcome_sha256",
    "candidate_id",
    "candidate_sha256",
    "media_content_sha256",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "requested_primary_asset_binding",
    "promotion_primary_asset_binding",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "promotion_status_record_id",
    "promotion_status_record_sha256",
    "promotion_status_receipt_id",
    "promotion_status_receipt_sha256",
    "promotion_explicit_chain_set_sha256",
    "promotion_coverage_set_sha256",
    "promotion_joint_replay_sha256",
    "promotion_as_of_assessment_sha256",
    "promotion_as_of_status",
    "promotion_status_valid_until",
    "checker_identity_ref_sha256",
    "checker_action_sha256",
    "checker_reviewed_at",
    "decision_at",
    "promotion_at",
    "gate_results",
    "promotion_issue_codes",
    "promotion_basis",
    "decision",
    "sidecar_materialization_allowed",
    "promotion_review_performed",
    "sidecar_id_embedded",
    "role_assignment_embedded",
    "provider_input_eligible",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_FIELDS,
)

_SIDECAR_PROJECTION_FIELDS = (
    "schema_version",
    "document_type",
    "sidecar_scope",
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "request_id",
    "request_sha256",
    "decision_id",
    "decision_sha256",
    "reference_prompt_artifact_sha256",
    "provider_attempt_outcome_id",
    "provider_attempt_outcome_sha256",
    "candidate_id",
    "candidate_sha256",
    "output_ordinal",
    "media_type",
    "media_content_sha256",
    "media_size_bytes",
    "media_technical_record_sha256",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "primary_asset_binding",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "promotion_status_record_id",
    "promotion_status_record_sha256",
    "promotion_status_receipt_id",
    "promotion_status_receipt_sha256",
    "promotion_explicit_chain_set_sha256",
    "promotion_coverage_set_sha256",
    "promotion_joint_replay_sha256",
    "promotion_as_of_assessment_sha256",
    "promotion_as_of_status",
    "promotion_at",
    "promotion_status_valid_until",
    "promotion_evidence_valid_until",
    "origin_claim",
    "origin_assurance",
    "sidecar_state",
    "promotion_performed",
    "eligible_for_separate_role_binding_review",
    "primary_asset_binding_replaced",
    "bible_active_binding_changed",
    "asset_version_v1_created",
    "composite_media_unsplit",
    "role_assignment_embedded",
    "provider_input_eligible",
    "present_currentness_asserted",
    "perpetual_eligibility_asserted",
    "supersedes_sidecar",
    "status",
    "evidence_scope",
    *_ZERO_AUTHORITY_FIELDS,
)

_REVIEW_PAYLOAD_FIELDS = (
    "policy_id",
    "policy_version",
    "policy_document_sha256",
    "request_scope",
    "reference_prompt_artifact_sha256",
    "provider_attempt_outcome_id",
    "provider_attempt_outcome_sha256",
    "candidate_id",
    "candidate_sha256",
    "output_ordinal",
    "media_type",
    "media_content_sha256",
    "media_size_bytes",
    "media_technical_record_sha256",
    "qualification_request_id",
    "qualification_request_sha256",
    "qualification_decision_id",
    "qualification_decision_sha256",
    "qualification_decision_at",
    "qualification_valid_until",
    "manifest_id",
    "manifest_sha256",
    "manifest_at",
    "manifest_valid_until",
    "reviewed_rights_scope",
    "status_subject_closure_id",
    "status_subject_closure_sha256",
    "requested_status_record_id",
    "requested_status_record_sha256",
    "requested_status_receipt_id",
    "requested_status_receipt_sha256",
    "requested_explicit_chain_set_sha256",
    "requested_coverage_set_sha256",
    "requested_joint_replay_sha256",
    "requested_as_of_assessment_sha256",
    "requested_as_of",
    "requested_as_of_status",
    "requested_status_valid_until",
    "requested_primary_asset_binding",
    "requested_at",
    "request_valid_until",
    "request_basis",
    "requested_representation",
    "composite_media_unsplit",
    "role_assignment_embedded",
    "bible_mutation_requested",
    "provider_input_requested",
)


def _semantic_sha256(domain: bytes, projection: object) -> str:
    return hashlib.sha256(domain + _compact_json(projection)).hexdigest()


def _rights_scope_projection(
    value: rights_module.GeneratedReferenceReviewedRightsScopeV1,
) -> dict[str, object]:
    if type(value) is not rights_module.GeneratedReferenceReviewedRightsScopeV1:
        _fail("known-answer Rights scope does not have the exact ADR-044 inline type")
    return {
        "territory_scope": list(value.territory_scope),
        "allowed_use_scope": list(value.allowed_use_scope),
        "reviewed_scope_valid_until": value.reviewed_scope_valid_until,
        "output_copyright_and_commercial_scope_basis": (
            value.output_copyright_and_commercial_scope_basis
        ),
        "likeness_privacy_and_sensitive_data_basis": (
            value.likeness_privacy_and_sensitive_data_basis
        ),
        "brand_and_protected_content_basis": value.brand_and_protected_content_basis,
        "retention_and_deletion_basis": value.retention_and_deletion_basis,
        "training_use_prohibition_basis": value.training_use_prohibition_basis,
        "review_basis": value.review_basis,
    }


def _primary_binding_projection(
    value: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1,
    *,
    include_digest: bool,
) -> dict[str, object]:
    if type(value) is not promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1:
        _fail("known-answer primary binding has the wrong exact type")
    projection: dict[str, object] = {
        "binding_profile": value.binding_profile,
        "asset_purpose": value.asset_purpose,
        "subject_id": value.subject_id,
        "asset_version_id": value.asset_version_id,
        "legacy_asset_version_projection_sha256": value.legacy_asset_version_projection_sha256,
        "version": value.version,
        "content_sha256": value.content_sha256,
        "media_type": value.media_type,
        "approval_ref": value.approval_ref,
        "provenance": value.provenance,
        "bible_active_asset_version_id": value.bible_active_asset_version_id,
    }
    if include_digest:
        projection["primary_asset_binding_sha256"] = value.primary_asset_binding_sha256
    return projection


def _gate_projection(
    value: promotion_module.GeneratedReferencePromotionGateResultV1,
) -> dict[str, object]:
    if type(value) is not promotion_module.GeneratedReferencePromotionGateResultV1:
        _fail("known-answer Promotion gate has the wrong exact type")
    return {
        "ordinal": value.ordinal,
        "gate": value.gate,
        "result": value.result,
        "basis": value.basis,
    }


def _projection_value(value: object) -> object:
    if type(value) is promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1:
        return _primary_binding_projection(
            value,
            include_digest=True,
        )
    if type(value) is rights_module.GeneratedReferenceReviewedRightsScopeV1:
        return _rights_scope_projection(value)
    if type(value) is promotion_module.GeneratedReferencePromotionGateResultV1:
        return _gate_projection(value)
    if type(value) is tuple:
        return [_projection_value(item) for item in cast(tuple[object, ...], value)]
    if type(value) is list:
        return [_projection_value(item) for item in cast(list[object], value)]
    if value is None or type(value) in {bool, int, str}:
        return value
    _fail("independent known-answer projection encountered an unapproved value type")


def _independent_contract_projection(value: object) -> dict[str, object]:
    fields: tuple[str, ...]
    if type(value) is promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        fields = _REQUEST_PROJECTION_FIELDS
    elif type(value) is promotion_module.CreativeSampleGeneratedReferenceAssetPromotionDecisionV1:
        fields = _DECISION_PROJECTION_FIELDS
    elif type(value) is promotion_module.CreativeSampleGeneratedReferenceEligibleAssetSidecarV1:
        fields = _SIDECAR_PROJECTION_FIELDS
    else:
        _fail("independent known-answer projection received an unapproved Contract type")
    return {name: _projection_value(getattr(value, name)) for name in fields}


def _independent_review_payload_projection(
    value: promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
) -> dict[str, object]:
    if type(value) is not promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1:
        _fail("independent review-payload calculator requires the exact Request type")
    return {name: _projection_value(getattr(value, name)) for name in _REVIEW_PAYLOAD_FIELDS}


def _independent_primary_asset_version_projection(
    value: CharacterAssetVersion | SceneAssetVersion,
) -> dict[str, object]:
    if type(value) is CharacterAssetVersion:
        character = value
        return {
            "approval_ref": character.approval_ref,
            "character_id": character.character_id,
            "content_sha256": character.content_sha256,
            "media_type": character.media_type,
            "provenance": character.provenance,
            "version": character.version,
            "visual_description": character.visual_description,
        }
    if type(value) is SceneAssetVersion:
        scene = value
        return {
            "approval_ref": scene.approval_ref,
            "content_sha256": scene.content_sha256,
            "media_type": scene.media_type,
            "provenance": scene.provenance,
            "scene_id": scene.scene_id,
            "version": scene.version,
            "visual_description": scene.visual_description,
        }
    _fail("independent primary AssetVersion calculator requires one exact released V1 type")


def _assert_independent_identities(
    *,
    asset_version: CharacterAssetVersion | SceneAssetVersion,
    binding: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1,
    request: promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
    decision: promotion_module.CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
    sidecar: promotion_module.CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
) -> dict[str, object]:
    legacy_projection = _independent_primary_asset_version_projection(asset_version)
    legacy_sha = hashlib.sha256(
        _PRIMARY_ASSET_VERSION_DOMAIN + _compact_json(legacy_projection)
    ).hexdigest()
    binding_projection = _primary_binding_projection(binding, include_digest=False)
    binding_sha = _semantic_sha256(_PRIMARY_BINDING_DOMAIN, binding_projection)
    request_projection = _independent_contract_projection(request)
    request_sha = _semantic_sha256(_REQUEST_DOMAIN, request_projection)
    review_projection = _independent_review_payload_projection(request)
    review_sha = _semantic_sha256(_REVIEW_PAYLOAD_DOMAIN, review_projection)
    decision_projection = _independent_contract_projection(decision)
    decision_sha = _semantic_sha256(_DECISION_DOMAIN, decision_projection)
    sidecar_projection = _independent_contract_projection(sidecar)
    sidecar_sha = _semantic_sha256(_SIDECAR_DOMAIN, sidecar_projection)
    expected = (
        legacy_sha == binding.legacy_asset_version_projection_sha256,
        binding_sha == binding.primary_asset_binding_sha256,
        request_sha == request.request_sha256,
        review_sha == request.promotion_review_payload_sha256,
        decision_sha == decision.decision_sha256,
        sidecar_sha == sidecar.sidecar_sha256,
        request.request_id == f"generated_reference_asset_promotion_request_v1_{request_sha[:20]}",
        decision.decision_id
        == f"generated_reference_asset_promotion_decision_v1_{decision_sha[:20]}",
        sidecar.sidecar_id
        == f"generated_reference_eligible_asset_sidecar_v1_{sidecar_sha[:20]}",
    )
    if not all(expected):
        _fail("independent ADR-045 known-answer identity calculation disagrees with core output")
    return {
        "legacy_primary_asset_version_projection": legacy_projection,
        "legacy_primary_asset_version_projection_sha256": legacy_sha,
        "primary_asset_binding_projection": binding_projection,
        "primary_asset_binding_sha256": binding_sha,
        "promotion_review_payload_projection": review_projection,
        "promotion_review_payload_sha256": review_sha,
        "request_projection": request_projection,
        "request_sha256": request_sha,
        "decision_projection": decision_projection,
        "decision_sha256": decision_sha,
        "sidecar_projection": sidecar_projection,
        "sidecar_sha256": sidecar_sha,
    }


def _parse_utc(value: object, *, field: str) -> datetime:
    if type(value) is not str or not value.endswith("Z") or len(value) != 20:
        _fail(f"{field} must use exact whole-second UTC Z text")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{field} is not one valid UTC second"
        ) from exc
    return parsed


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_canonical_document(raw: bytes, *, label: str) -> dict[str, object]:
    if not raw or raw.startswith(_UTF8_BOM) or b"\r" in raw:
        _fail(f"{label} must use nonempty UTF-8, LF-only, no-BOM bytes")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        _fail(f"{label} must end with exactly one LF")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} is not strict UTF-8 JSON"
        ) from exc
    if type(value) is not dict:
        _fail(f"{label} must have an object root")
    _validate_json_value(value)
    if _canonical_document_bytes(value) != raw:
        _fail(f"{label} is not the frozen persistent canonical JSON document")
    return cast(dict[str, object], value)


def _explicit(value: object) -> object:
    if hasattr(value, "model_dump"):
        return cast(object, value.model_dump(mode="json"))
    if isinstance(value, tuple):
        return [_explicit(item) for item in value]
    if isinstance(value, list):
        return [_explicit(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _explicit(item) for key, item in value.items()}
    return value


def _identity_record(value: object, *, label: str) -> dict[str, object]:
    expected_keys = {"document_profile", "identity_namespace", "identity_ref"}
    if type(value) is not dict or set(cast(dict[str, object], value)) != expected_keys:
        _fail(f"{label} must use the frozen privacy-minimized identity shape")
    result = cast(dict[str, object], value)
    if (
        result.get("document_profile") != "sdc.privacy-minimized-human-reference.v1"
        or type(result.get("identity_namespace")) is not str
        or type(result.get("identity_ref")) is not str
    ):
        _fail(f"{label} is not one exact retained semantic identity")
    return result


def _source_case(value: dict[str, object], case_id: str) -> dict[str, object]:
    cases = value.get("cases")
    if type(cases) is not list:
        _fail("reviewed source cases must be one exact array")
    matches = [
        item
        for item in cast(list[object], cases)
        if type(item) is dict and cast(dict[str, object], item).get("case_id") == case_id
    ]
    if len(matches) != 1:
        _fail(f"reviewed source must contain exactly one {case_id} case")
    return cast(dict[str, object], matches[0])


def _assert_promotion_source(case: dict[str, object]) -> None:
    case_id = cast(str, case["case_id"])
    promotion = case.get("promotion")
    if type(promotion) is not dict:
        _fail(f"{case_id} Promotion review source is missing")
    promotion = cast(dict[str, object], promotion)
    expected_keys = {
        "checker_identity_record",
        "decision",
        "human_gate_results",
        "maker_identity_record",
        "promotion_at",
        "promotion_basis",
        "request_basis",
        "requested_at",
        "sidecar_materialization_allowed",
    }
    if set(promotion) != expected_keys:
        _fail(f"{case_id} Promotion review source fields are not frozen")
    maker = _identity_record(
        promotion.get("maker_identity_record"), label=f"{case_id} Promotion Maker"
    )
    checker = _identity_record(
        promotion.get("checker_identity_record"), label=f"{case_id} Promotion Checker"
    )
    if (maker["identity_namespace"], maker["identity_ref"]) == (
        checker["identity_namespace"],
        checker["identity_ref"],
    ):
        _fail(f"{case_id} Promotion Maker and Checker identities must differ")
    if (
        promotion.get("decision") != "APPROVE_ELIGIBLE_ASSET_SIDECAR"
        or promotion.get("sidecar_materialization_allowed") is not True
        or any(
            type(promotion.get(name)) is not str
            for name in ("promotion_at", "promotion_basis", "request_basis", "requested_at")
        )
    ):
        _fail(f"{case_id} is not the frozen positive Promotion known answer")
    raw_gates = promotion.get("human_gate_results")
    expected_gates = (
        "HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED",
        "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED",
    )
    if type(raw_gates) is not list or len(raw_gates) != 2:
        _fail(f"{case_id} must contain exactly two Promotion human gate results")
    for raw_gate, expected_gate in zip(
        cast(list[object], raw_gates), expected_gates, strict=True
    ):
        if (
            type(raw_gate) is not dict
            or set(cast(dict[str, object], raw_gate)) != {"basis", "gate", "result"}
            or cast(dict[str, object], raw_gate).get("gate") != expected_gate
            or cast(dict[str, object], raw_gate).get("result") != "PASS"
            or type(cast(dict[str, object], raw_gate).get("basis")) is not str
        ):
            _fail(f"{case_id} Promotion human gate order or positive result drifted")


def _assert_primary_asset_source(case: dict[str, object]) -> None:
    case_id = cast(str, case["case_id"])
    value = case.get("primary_asset_source")
    if type(value) is not dict:
        _fail(f"{case_id} primary AssetVersion source is missing")
    value = cast(dict[str, object], value)
    expected_keys = {
        "case_id",
        "expected_asset_version_id",
        "expected_content_sha256",
        "fixture_path",
    }
    expected_id_and_sha = {
        _CASE_IDS[0]: (
            "character_asset_3087686f6e50d9cdcf1c",
            "ee75137f45903e71783f4a67caa97b1373ce7f5b47e6f422508bef88be86f77d",
        ),
        _CASE_IDS[1]: (
            "scene_asset_56f69f399a1e9fd2f482",
            "4ba7559edf922ba6ca29accb1239e6232138ebcd55e7ea86465862e227c4adfc",
        ),
    }
    expected_id, expected_sha = expected_id_and_sha[case_id]
    if (
        set(value) != expected_keys
        or value.get("fixture_path") != _PRIMARY_ASSET_SOURCE_PATH
        or value.get("case_id") != _PRIMARY_ASSET_CASE_IDS[case_id]
        or value.get("expected_asset_version_id") != expected_id
        or value.get("expected_content_sha256") != expected_sha
    ):
        _fail(f"{case_id} primary AssetVersion source anchor drifted")


def _assert_upstream_source(case: dict[str, object]) -> None:
    case_id = cast(str, case["case_id"])
    value = case.get("upstream")
    if type(value) is not dict:
        _fail(f"{case_id} upstream source is missing")
    value = cast(dict[str, object], value)
    common_paths = {
        "candidate_generated_fixture_path": _CANDIDATE_GENERATED_PATH,
        "candidate_source_fixture_path": _CANDIDATE_SOURCE_PATH,
        "png_path": _CHARACTER_PNG_PATH if case_id == _CASE_IDS[0] else _SCENE_PNG_PATH,
    }
    for name, expected in common_paths.items():
        if value.get(name) != expected:
            _fail(f"{case_id} references an unfrozen upstream fixture or PNG")
    if case_id == _CASE_IDS[0]:
        if (
            value.get("candidate_case_id") != "character-reference-pass"
            or value.get("rights_case_id") != "character-reference-current-v1"
            or value.get("rights_generated_fixture_path") != _RIGHTS_GENERATED_PATH
            or value.get("rights_source_fixture_path") != _RIGHTS_SOURCE_PATH
        ):
            _fail("Character Promotion must reuse the exact ADR-044 positive closure")
    elif value.get("candidate_case_id") != "scene-reference-pass":
        _fail("Scene Promotion must reuse the exact ADR-043 scene closure")
    for name in (
        "artifact_sha256",
        "candidate_id",
        "candidate_sha256",
        "media_content_sha256",
        "provider_attempt_outcome_id",
        "provider_attempt_outcome_sha256",
        "subject_id",
    ):
        if type(value.get(name)) is not str:
            _fail(f"{case_id} upstream anchor {name} is missing")
    if type(value.get("media_size_bytes")) is not int:
        _fail(f"{case_id} upstream media_size_bytes is missing")


def _assert_scene_status_source(
    value: object,
    *,
    case: dict[str, object],
    label: str,
    expected_count: int,
    expected_target_count: int,
) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"Scene {label} status source is missing")
    result = cast(dict[str, object], value)
    expected_keys = {
        "as_of",
        "checker_basis",
        "checker_role",
        "evaluated_at",
        "expected_as_of_status",
        "expected_recorded_status",
        "expected_request_valid_until",
        "expected_status_valid_until",
        "limitation_codes",
        "observations",
        "preparer_role",
        "request_basis",
        "requested_at",
    }
    if set(result) != expected_keys:
        _fail(f"Scene {label} status source fields are not frozen")
    if (
        result.get("expected_as_of_status") != "CURRENT"
        or result.get("expected_recorded_status") != "CURRENT"
        or any(
            type(result.get(name)) is not str
            for name in (
                "as_of",
                "checker_basis",
                "checker_role",
                "evaluated_at",
                "expected_request_valid_until",
                "expected_status_valid_until",
                "preparer_role",
                "request_basis",
                "requested_at",
            )
        )
    ):
        _fail(f"Scene {label} status source is not a complete CURRENT known answer")
    promotion = cast(dict[str, object], case["promotion"])
    expected_as_of = (
        promotion["requested_at"] if label == "request-time" else promotion["promotion_at"]
    )
    if result.get("as_of") != expected_as_of:
        _fail(f"Scene {label} Receipt as_of does not bind the Promotion timeline")
    observations = result.get("observations")
    if type(observations) is not list or len(observations) != expected_count:
        _fail(f"Scene {label} status observation count drifted")
    observation_keys: list[str] = []
    target_count = 0
    link_counts = {"GENESIS": 0, "SUCCESSOR": 0, "RECONCILIATION": 0}
    for raw in cast(list[object], observations):
        if type(raw) is not dict:
            _fail(f"Scene {label} status observation must be one object")
        observation = cast(dict[str, object], raw)
        required = {
            "basis_code",
            "basis_note",
            "category",
            "claim_value",
            "link_kind",
            "observation_key",
            "observed_at",
            "predecessor_observation_keys",
            "source_event_at",
            "source_kind",
            "source_object",
            "source_object_media_type",
            "source_object_ref",
            "source_reference",
            "target",
            "valid_from",
            "valid_until",
        }
        if set(observation) != required:
            _fail(f"Scene {label} status observation fields drifted")
        key = observation.get("observation_key")
        link_kind = observation.get("link_kind")
        predecessors = observation.get("predecessor_observation_keys")
        if (
            type(key) is not str
            or link_kind not in link_counts
            or type(predecessors) is not list
            or any(type(item) is not str for item in cast(list[object], predecessors))
            or type(observation.get("target")) is not bool
        ):
            _fail(f"Scene {label} status topology is malformed")
        observation_keys.append(key)
        target_count += int(cast(bool, observation["target"]))
        link_counts[link_kind] += 1
        predecessor_count = len(cast(list[object], predecessors))
        if (
            (link_kind == "GENESIS" and predecessor_count != 0)
            or (link_kind == "SUCCESSOR" and predecessor_count != 1)
            or (link_kind == "RECONCILIATION" and predecessor_count < 2)
        ):
            _fail(f"Scene {label} status predecessor cardinality drifted")
    if len(observation_keys) != len(set(observation_keys)) or target_count != expected_target_count:
        _fail(f"Scene {label} status target/key cardinality drifted")
    if label == "request-time" and link_counts != {
        "GENESIS": 9,
        "SUCCESSOR": 0,
        "RECONCILIATION": 0,
    }:
        _fail("Scene request-time status must be the exact nine-category genesis set")
    if label == "promotion-time" and link_counts != {
        "GENESIS": 10,
        "SUCCESSOR": 2,
        "RECONCILIATION": 1,
    }:
        _fail("Scene promotion-time status must contain the frozen successor/reconciliation plan")
    return result


def _assert_scene_rights_source(case: dict[str, object]) -> None:
    value = case.get("scene_rights_current_status")
    if type(value) is not dict:
        _fail("Scene Rights/current-status source is missing")
    value = cast(dict[str, object], value)
    if set(value) != {"manifest", "promotion_status", "request_status", "synthetic_role_records"}:
        _fail("Scene Rights/current-status source fields are not frozen")
    manifest = value.get("manifest")
    if type(manifest) is not dict or set(cast(dict[str, object], manifest)) != {
        "expected_manifest_valid_until",
        "human_gate_reviews",
        "manifest_at",
        "proposed_rights_scope",
        "review_evidence_documents",
        "reviewed_rights_scope",
    }:
        _fail("Scene Manifest source fields are not frozen")
    manifest = cast(dict[str, object], manifest)
    if (
        type(manifest.get("review_evidence_documents")) is not list
        or len(cast(list[object], manifest["review_evidence_documents"])) != 9
        or type(manifest.get("human_gate_reviews")) is not list
        or len(cast(list[object], manifest["human_gate_reviews"])) != 9
    ):
        _fail("Scene Manifest must contain exactly nine evidence records and human gates")
    roles = value.get("synthetic_role_records")
    expected_roles = (
        "QUALIFICATION_QUALIFIER",
        "MANIFEST_MAKER",
        "MANIFEST_CHECKER",
        "REQUEST_STATUS_PREPARER",
        "REQUEST_STATUS_CHECKER",
        "FINAL_STATUS_PREPARER",
        "FINAL_STATUS_CHECKER",
    )
    if type(roles) is not list or tuple(
        item.get("role") if type(item) is dict else None for item in cast(list[object], roles)
    ) != expected_roles:
        _fail("Scene synthetic retained role order is not frozen")
    for raw_role in cast(list[object], roles):
        role = cast(dict[str, object], raw_role)
        if set(role) != {"action_semantics", "identity_record", "role"}:
            _fail("Scene retained role fields are not frozen")
        _identity_record(role.get("identity_record"), label=cast(str, role["role"]))
        if type(role.get("action_semantics")) is not dict:
            _fail("Scene retained action semantics are missing")
    request_status = _assert_scene_status_source(
        value.get("request_status"),
        case=case,
        label="request-time",
        expected_count=9,
        expected_target_count=9,
    )
    promotion_status = _assert_scene_status_source(
        value.get("promotion_status"),
        case=case,
        label="promotion-time",
        expected_count=13,
        expected_target_count=10,
    )
    request_observations: dict[str, dict[str, object]] = {
        cast(str, cast(dict[str, object], item)["observation_key"]): cast(
            dict[str, object], item
        )
        for item in cast(list[object], request_status["observations"])
    }
    promotion_observations: dict[str, dict[str, object]] = {
        cast(str, cast(dict[str, object], item)["observation_key"]): cast(
            dict[str, object], item
        )
        for item in cast(list[object], promotion_status["observations"])
    }
    if not request_observations.keys() <= promotion_observations.keys() or any(
        {
            name: value
            for name, value in promotion_observations[key].items()
            if name != "target"
        }
        != {name: value for name, value in item.items() if name != "target"}
        for key, item in request_observations.items()
    ):
        _fail("Scene promotion-time status must retain every request-time occurrence byte-exactly")


def _assert_source_shape(value: dict[str, object]) -> tuple[dict[str, object], ...]:
    if tuple(value) != _ROOT_KEYS or value.get("known_answer_version") != _KNOWN_ANSWER_VERSION:
        _fail("reviewed source root keys or known_answer_version are not frozen")
    cases = value.get("cases")
    if type(cases) is not list or tuple(
        item.get("case_id") if type(item) is dict else None for item in cast(list[object], cases)
    ) != _CASE_IDS:
        _fail("reviewed source must contain the two frozen case IDs in order")
    scope = value.get("source_packet_scope")
    expected_scope = {
        "asset_promotion_authority_granted": False,
        "automated_execution_allowed": False,
        "commercial_use_rights_proven": False,
        "content_origin": "FIRST_PARTY_SYNTHETIC_TEST_CONTENT",
        "generation_authorized": False,
        "identity_authentication_claimed": False,
        "network_allowed": False,
        "provider_input_allowed": False,
        "provider_requests": 0,
        "publication_allowed": False,
        "purpose": "Offline deterministic SDC-ADR-045 promotion known-answer review only",
        "real_world_currentness_asserted": False,
        "real_world_eligibility_asserted": False,
        "retention_allowed": False,
        "role_binding_authorized": False,
        "training_allowed": False,
    }
    if (
        type(scope) is not dict
        or set(cast(dict[str, object], scope)) != set(expected_scope)
        or any(
            type(cast(dict[str, object], scope).get(name)) is not type(expected)
            or cast(dict[str, object], scope).get(name) != expected
            for name, expected in expected_scope.items()
        )
    ):
        _fail("reviewed source packet scope is not the frozen zero-authority declaration")
    typed_cases = tuple(cast(dict[str, object], item) for item in cast(list[object], cases))
    for case in typed_cases:
        expected_keys = {
            "case_id",
            "primary_asset_source",
            "promotion",
            "status_plan",
            "upstream",
        }
        if case["case_id"] == _CASE_IDS[1]:
            expected_keys.add("scene_rights_current_status")
        if set(case) != expected_keys:
            _fail(f"{case['case_id']} reviewed source fields are not frozen")
        _assert_primary_asset_source(case)
        _assert_upstream_source(case)
        _assert_promotion_source(case)
    if typed_cases[0].get("status_plan") != (
        "REUSE_ADR044_COMPLETE_RECORD_FOR_REQUEST_AND_PROMOTION_REPLAY"
    ):
        _fail("Character status plan must reuse the same complete ADR-044 Record")
    if typed_cases[1].get("status_plan") != (
        "MONOTONIC_SUCCESSOR_RECONCILIATION_WITH_RECANONICALIZED_TARGET_ORDINALS"
    ):
        _fail("Scene status plan must exercise the frozen monotonic final-Record path")
    _assert_scene_rights_source(typed_cases[1])
    return typed_cases


def _assert_fixed_paths() -> None:
    paths = (*_PROTECTED_FINGERPRINTS, _DERIVED_FIXTURE_PATH)
    if len(paths) != len(set(paths)):
        _fail("source, old fixtures and derived fixture paths must be distinct")
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
    if Path(_REVIEWED_SOURCE_PATH).parent != Path(_FIXTURE_DIRECTORY) or Path(
        _DERIVED_FIXTURE_PATH
    ).parent != Path(_FIXTURE_DIRECTORY):
        _fail("ADR-045 source and derived fixtures must share their fixed directory")
    if len(_FROZEN_OLD_FIXTURE_FINGERPRINTS) != 16:
        _fail("the frozen old visual-prompt fixture inventory must contain exactly sixteen paths")
    required_upstream = {
        _CANDIDATE_SOURCE_PATH,
        _CANDIDATE_GENERATED_PATH,
        _CHARACTER_PNG_PATH,
        _SCENE_PNG_PATH,
        _RIGHTS_SOURCE_PATH,
        _RIGHTS_GENERATED_PATH,
        _PRIMARY_ASSET_SOURCE_PATH,
    }
    if not required_upstream <= set(_FROZEN_OLD_FIXTURE_FINGERPRINTS):
        _fail("one fixed ADR-042/043/044 upstream path is outside the frozen inventory")


def _safe_path(root: Path, relative_path: str, *, label: str) -> Path:
    if not root.is_absolute():
        _fail(f"{label} repository root must be absolute")
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        _fail(f"{label} path is not one fixed repository-relative path")
    try:
        root_info = os.lstat(root)
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "repository root is missing or inaccessible"
        ) from exc
    if not _is_directory_non_symlink(root_info):
        _fail("repository root must be one regular non-symlink directory")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise GeneratedReferenceAssetPromotionCodegenError(
                f"{label} ancestor is missing or inaccessible"
            ) from exc
        if not _is_directory_non_symlink(info):
            _fail(f"{label} ancestors must be regular non-symlink directories")
    candidate = root / relative
    try:
        resolved_root = root.resolve()
        if os.path.commonpath(
            (str(resolved_root), str(candidate.resolve(strict=False)))
        ) != str(resolved_root):
            _fail(f"{label} escapes the fixed repository root")
    except (OSError, ValueError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} could not be anchored inside the repository"
        ) from exc
    return candidate


def _read_frozen(
    root: Path,
    relative_path: str,
    *,
    max_bytes: int,
    label: str,
) -> bytes:
    path = _safe_path(root, relative_path, label=label)
    raw = _read_stable_regular_file(path, max_bytes=max_bytes, label=label)
    expected_size, expected_sha = _PROTECTED_FINGERPRINTS[relative_path]
    if expected_size <= 0 or len(expected_sha) != 64:
        _fail("reviewed source byte size and raw SHA-256 have not been frozen")
    if len(raw) != expected_size or _raw_sha256(raw) != expected_sha:
        _fail(f"{label} does not have its frozen exact bytes")
    return raw


@dataclass(frozen=True, slots=True)
class _ProtectedInputs:
    reviewed_source_raw: bytes
    reviewed_source: dict[str, object]
    old_fixture_raws: tuple[tuple[str, bytes], ...]

    def raw(self, relative_path: str) -> bytes:
        for path, raw in self.old_fixture_raws:
            if path == relative_path:
                return raw
        _fail("requested upstream path is outside the fixed old-fixture inventory")


@dataclass(frozen=True, slots=True)
class _ExpectedClosure:
    protected: _ProtectedInputs
    derived_value: dict[str, object]
    derived_raw: bytes


def _load_protected_inputs(root: Path) -> _ProtectedInputs:
    _assert_fixed_paths()
    reviewed_raw = _read_frozen(
        root,
        _REVIEWED_SOURCE_PATH,
        max_bytes=_MAX_SOURCE_BYTES,
        label="reviewed source fixture",
    )
    old_raws: list[tuple[str, bytes]] = []
    for relative_path in _FROZEN_OLD_FIXTURE_FINGERPRINTS:
        maximum = _MAX_PNG_BYTES if relative_path.endswith(".png") else _MAX_OLD_FIXTURE_BYTES
        old_raws.append(
            (
                relative_path,
                _read_frozen(
                    root,
                    relative_path,
                    max_bytes=maximum,
                    label=f"frozen old fixture {relative_path}",
                ),
            )
        )
    reviewed = _parse_canonical_document(reviewed_raw, label="reviewed source fixture")
    _assert_source_shape(reviewed)
    return _ProtectedInputs(
        reviewed_source_raw=reviewed_raw,
        reviewed_source=reviewed,
        old_fixture_raws=tuple(old_raws),
    )


@dataclass(frozen=True, slots=True)
class _KnownAnswerMaterials:
    upstream: promotion_module.GeneratedReferenceAssetPromotionUpstreamClosureInput
    request_status: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput
    final_status: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput
    primary_bible: CharacterBible | SceneBible
    primary_asset_version: CharacterAssetVersion | SceneAssetVersion


def _document_case(
    value: dict[str, object], *, case_id: str, label: str
) -> dict[str, object]:
    cases = value.get("cases")
    if type(cases) is not list:
        cases = value.get("positive_cases")
    if type(cases) is not list:
        _fail(f"{label} does not contain one explicit case array")
    matches = [
        item
        for item in cast(list[object], cases)
        if type(item) is dict and cast(dict[str, object], item).get("case_id") == case_id
    ]
    if len(matches) != 1:
        _fail(f"{label} must contain exactly one {case_id} case")
    return cast(dict[str, object], matches[0])


def _model_from_value(value: object, model_type: type[BaseModel], *, label: str) -> BaseModel:
    try:
        validator = model_type.model_validate_json
        return validator(_canonical_document_bytes(value), strict=True)
    except (AttributeError, TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            f"{label} does not validate as its exact frozen model"
        ) from exc


def _old_json(protected: _ProtectedInputs, relative_path: str, *, label: str) -> dict[str, object]:
    return _parse_canonical_document(protected.raw(relative_path), label=label)


def _primary_asset_closure(
    protected: _ProtectedInputs, case: dict[str, object]
) -> tuple[
    CharacterBible | SceneBible,
    CharacterAssetVersion | SceneAssetVersion,
]:
    source = _old_json(
        protected,
        _PRIMARY_ASSET_SOURCE_PATH,
        label="frozen ADR-042 primary AssetVersion source fixture",
    )
    primary = cast(dict[str, object], case["primary_asset_source"])
    source_case = _document_case(
        source,
        case_id=cast(str, primary["case_id"]),
        label="frozen ADR-042 primary AssetVersion source fixture",
    )
    subject = source_case.get("subject")
    case_id = cast(str, case["case_id"])
    bible: CharacterBible | SceneBible
    asset: CharacterAssetVersion | SceneAssetVersion
    if case_id == _CASE_IDS[0]:
        character_bible = cast(
            CharacterBible,
            _model_from_value(subject, CharacterBible, label="CharacterBible"),
        )
        character_matches = tuple(
            item
            for item in character_bible.asset_versions
            if item.id == character_bible.active_asset_version_id
        )
        if len(character_matches) != 1 or type(character_matches[0]) is not CharacterAssetVersion:
            _fail("Character primary Bible does not have one exact active AssetVersion")
        bible = character_bible
        asset = character_matches[0]
    else:
        scene_bible = cast(
            SceneBible,
            _model_from_value(subject, SceneBible, label="SceneBible"),
        )
        scene_matches = tuple(
            item
            for item in scene_bible.asset_versions
            if item.id == scene_bible.active_asset_version_id
        )
        if len(scene_matches) != 1 or type(scene_matches[0]) is not SceneAssetVersion:
            _fail("Scene primary Bible does not have one exact active AssetVersion")
        bible = scene_bible
        asset = scene_matches[0]
    if (
        asset.id != primary.get("expected_asset_version_id")
        or asset.content_sha256 != primary.get("expected_content_sha256")
    ):
        _fail("primary AssetVersion does not match the reviewed source anchor")
    return bible, asset


def _manifest_evidence_inputs(
    manifest_closure: rights_codegen._ManifestClosure,
) -> tuple[rights_module.GeneratedReferenceRightsManifestEvidenceInput, ...]:
    manifest = manifest_closure.manifest
    documents = manifest_closure.review_evidence_documents
    if len(documents) != len(manifest.review_evidence_refs) or len(documents) != 9:
        _fail("Manifest known answer does not carry the complete nine-document closure")
    return tuple(
        rights_module.GeneratedReferenceRightsManifestEvidenceInput(
            reference=reference,
            document_bytes=raw,
        )
        for reference, raw in zip(manifest.review_evidence_refs, documents, strict=True)
    )


def _proposed_rights_scope(
    source: dict[str, object],
) -> rights_module.GeneratedReferenceRightsScopeProposalV1:
    value = source.get("proposed_rights_scope")
    if type(value) is not dict:
        _fail("Manifest proposed Rights scope source is missing")
    values = dict(cast(dict[str, object], value))
    for name in ("territory_scope", "allowed_use_scope"):
        raw = values.get(name)
        if type(raw) is not list:
            _fail("Manifest proposed Rights scope tuple source is malformed")
        values[name] = tuple(cast(list[object], raw))
    try:
        return rights_module.GeneratedReferenceRightsScopeProposalV1.model_validate(values)
    except (TypeError, ValueError, ValidationError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "Manifest proposed Rights scope does not validate"
        ) from exc


def _upstream_input(
    *,
    upstream_closure: rights_codegen._UpstreamClosure,
    manifest_closure: rights_codegen._ManifestClosure,
    manifest_source: dict[str, object],
) -> promotion_module.GeneratedReferenceAssetPromotionUpstreamClosureInput:
    return promotion_module.GeneratedReferenceAssetPromotionUpstreamClosureInput(
        artifact=upstream_closure.artifact,
        outcome=upstream_closure.outcome,
        candidate=upstream_closure.candidate,
        qualification_request=upstream_closure.qualification_request,
        qualification_decision=upstream_closure.qualification_decision,
        png_bytes=upstream_closure.png_bytes,
        qualification_evidence_documents=upstream_closure.evidence_inputs,
        qualification_preparer_identity_bytes=upstream_closure.preparer_identity_bytes,
        qualification_preparer_action_bytes=upstream_closure.preparer_action_bytes,
        qualifier_identity_bytes=upstream_closure.qualifier_identity_bytes,
        qualifier_action_bytes=upstream_closure.qualifier_action_bytes,
        manifest=manifest_closure.manifest,
        manifest_review_evidence_documents=_manifest_evidence_inputs(manifest_closure),
        manifest_proposed_rights_scope=_proposed_rights_scope(manifest_source),
        manifest_maker_identity_bytes=manifest_closure.maker_identity_bytes,
        manifest_maker_action_bytes=manifest_closure.maker_action_bytes,
        manifest_checker_identity_bytes=manifest_closure.checker_identity_bytes,
        manifest_checker_action_bytes=manifest_closure.checker_action_bytes,
        manifest_at=cast(str, manifest_source["manifest_at"]),
    )


def _status_input_from_adr044(
    closure: rights_codegen._CurrentStatusClosure,
    *,
    receipt: _StatusReceipt,
) -> promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput:
    return promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput(
        subject_closure=closure.subject_closure,
        request=closure.request,
        instruction=closure.instruction,
        decision=closure.decision,
        record=closure.evidence_record,
        chain_inputs=closure.chain_inputs,
        receipt=receipt,
        status_preparer_identity_bytes=closure.preparer_identity_bytes,
        status_preparer_action_bytes=closure.preparer_action_bytes,
        status_checker_identity_bytes=closure.checker_identity_bytes,
        status_checker_action_bytes=closure.checker_action_bytes,
    )


def _assert_frozen_adr044_generated_closure(
    protected: _ProtectedInputs,
    *,
    rights_protected: rights_codegen._ProtectedInputs,
    upstream: rights_codegen._UpstreamClosure,
    manifest: rights_codegen._ManifestClosure,
    current: rights_codegen._CurrentStatusClosure,
) -> None:
    generated = _old_json(
        protected,
        _RIGHTS_GENERATED_PATH,
        label="frozen ADR-044 generated known-answer fixture",
    )
    expected_root_keys = {
        "current_status_policy_document_sha256",
        "historical_qualification_expiry_cases",
        "known_answer_version",
        "manifest_policy_document_sha256",
        "positive_cases",
        "reviewed_source",
        "upstream_inputs",
    }
    positive_cases = generated.get("positive_cases")
    if (
        set(generated) != expected_root_keys
        or generated.get("known_answer_version") != "1.0.0"
        or type(positive_cases) is not list
        or len(positive_cases) != 1
    ):
        _fail("frozen ADR-044 generated fixture root or positive-case cardinality drifted")
    generated_case = _document_case(
        generated,
        case_id="character-reference-current-v1",
        label="frozen ADR-044 generated known-answer fixture",
    )
    explicit_chain_inputs = [
        {
            "target_observation_refs": [
                _explicit(item) for item in chain.target_observation_refs
            ],
            "observations": [
                _explicit(item.observation) for item in chain.observation_inputs
            ],
        }
        for chain in current.chain_inputs
    ]
    assessment = current.process_result.assessment
    expected_case = {
        "case_id": "character-reference-current-v1",
        "artifact": _explicit(upstream.artifact),
        "provider_attempt_outcome": _explicit(upstream.outcome),
        "candidate": _explicit(upstream.candidate),
        "qualification_request": _explicit(upstream.qualification_request),
        "qualification_decision": _explicit(upstream.qualification_decision),
        "rights_manifest": _explicit(manifest.manifest),
        "subject_closure": _explicit(current.subject_closure),
        "source_observations": [
            _explicit(item.observation) for item in current.observation_inputs
        ],
        "current_status_request": _explicit(current.request),
        "current_status_instruction": _explicit(current.instruction),
        "current_status_decision": _explicit(current.decision),
        "current_status_evidence_record": _explicit(current.evidence_record),
        "explicit_chain_inputs": explicit_chain_inputs,
        "record_as_of_assessment": {
            "as_of": assessment.as_of,
            "as_of_assessment_sha256": assessment.as_of_assessment_sha256,
            "as_of_status": assessment.as_of_status,
            "coverage_set_sha256": assessment.coverage_set_sha256,
            "explicit_chain_set_sha256": assessment.explicit_chain_set_sha256,
            "joint_replay_sha256": assessment.joint_replay_sha256,
            "recorded_status": assessment.recorded_status,
            "status_valid_until": assessment.status_valid_until,
        },
        "record_as_of_assessment_receipt": _explicit(current.process_result.receipt),
    }
    expected_generated = {
        "current_status_policy_document_sha256": (
            rights_module.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
        ),
        "historical_qualification_expiry_cases": (
            rights_codegen._historical_expiry_results(rights_protected)
        ),
        "known_answer_version": "1.0.0",
        "manifest_policy_document_sha256": (
            rights_module.GENERATED_REFERENCE_RIGHTS_MANIFEST_POLICY_DOCUMENT_SHA256
        ),
        "positive_cases": [expected_case],
        "reviewed_source": {
            "path": _RIGHTS_SOURCE_PATH,
            "raw_sha256": _raw_sha256(rights_protected.reviewed_source_raw),
            "size_bytes": len(rights_protected.reviewed_source_raw),
        },
        "upstream_inputs": {
            "candidate_generated_fixture_path": _CANDIDATE_GENERATED_PATH,
            "candidate_generated_raw_sha256": _raw_sha256(
                rights_protected.candidate_generated_raw
            ),
            "candidate_generated_size_bytes": len(
                rights_protected.candidate_generated_raw
            ),
            "candidate_source_fixture_path": _CANDIDATE_SOURCE_PATH,
            "candidate_source_raw_sha256": _raw_sha256(
                rights_protected.candidate_source_raw
            ),
            "candidate_source_size_bytes": len(rights_protected.candidate_source_raw),
            "character_png_path": _CHARACTER_PNG_PATH,
            "character_png_raw_sha256": _raw_sha256(
                rights_protected.character_png_raw
            ),
            "character_png_size_bytes": len(rights_protected.character_png_raw),
        },
    }
    if generated_case != expected_case or generated != expected_generated:
        _fail(
            "frozen ADR-044 generated Qualification/Manifest/current-status closure "
            "differs from its complete independent source rebuild"
        )


def _assert_upstream_anchors(
    case: dict[str, object],
    upstream: promotion_module.GeneratedReferenceAssetPromotionUpstreamClosureInput,
) -> None:
    expected = cast(dict[str, object], case["upstream"])
    actual = {
        "artifact_sha256": upstream.artifact.artifact_sha256,
        "candidate_id": upstream.candidate.candidate_id,
        "candidate_sha256": upstream.candidate.candidate_sha256,
        "media_content_sha256": _raw_sha256(upstream.png_bytes),
        "media_size_bytes": len(upstream.png_bytes),
        "provider_attempt_outcome_id": upstream.outcome.outcome_id,
        "provider_attempt_outcome_sha256": upstream.outcome.outcome_sha256,
        "subject_id": upstream.candidate.subject_id,
    }
    if any(expected.get(name) != value for name, value in actual.items()):
        _fail(f"{case['case_id']} copied upstream anchors do not match exact objects/bytes")


def _character_materials(
    protected: _ProtectedInputs, case: dict[str, object]
) -> _KnownAnswerMaterials:
    candidate_source_raw = protected.raw(_CANDIDATE_SOURCE_PATH)
    candidate_generated_raw = protected.raw(_CANDIDATE_GENERATED_PATH)
    rights_source_raw = protected.raw(_RIGHTS_SOURCE_PATH)
    rights_protected = rights_codegen._ProtectedInputs(
        reviewed_source_raw=rights_source_raw,
        reviewed_source=_parse_canonical_document(
            rights_source_raw, label="frozen ADR-044 reviewed source fixture"
        ),
        candidate_source_raw=candidate_source_raw,
        candidate_source=_parse_canonical_document(
            candidate_source_raw, label="frozen ADR-043 reviewed source fixture"
        ),
        candidate_generated_raw=candidate_generated_raw,
        candidate_generated=_parse_canonical_document(
            candidate_generated_raw, label="frozen ADR-043 generated fixture"
        ),
        character_png_raw=protected.raw(_CHARACTER_PNG_PATH),
    )
    source_case = rights_codegen._assert_source_shape(rights_protected.reviewed_source)
    upstream_closure = rights_codegen._build_upstream(rights_protected, source_case)
    manifest_closure = rights_codegen._build_manifest(source_case, upstream_closure)
    status_closure = rights_codegen._build_current_status(source_case, manifest_closure)
    _assert_frozen_adr044_generated_closure(
        protected,
        rights_protected=rights_protected,
        upstream=upstream_closure,
        manifest=manifest_closure,
        current=status_closure,
    )
    manifest_source = cast(dict[str, object], source_case["manifest"])
    upstream = _upstream_input(
        upstream_closure=upstream_closure,
        manifest_closure=manifest_closure,
        manifest_source=manifest_source,
    )
    request_receipt = status_closure.process_result.receipt
    request_status = _status_input_from_adr044(status_closure, receipt=request_receipt)
    promotion_at = cast(str, cast(dict[str, object], case["promotion"])["promotion_at"])
    final_process = _process_status_record_as_of(
        status_closure.evidence_record,
        manifest_closure.manifest,
        status_closure.chain_inputs,
        as_of=promotion_at,
    )
    rights_module.verify_generated_reference_current_status_record_as_of_assessment_receipt(
        final_process.receipt,
        record=status_closure.evidence_record,
        manifest=manifest_closure.manifest,
        chain_inputs=status_closure.chain_inputs,
    )
    final_status = _status_input_from_adr044(
        status_closure,
        receipt=final_process.receipt,
    )
    bible, asset = _primary_asset_closure(protected, case)
    _assert_upstream_anchors(case, upstream)
    if request_receipt.as_of != cast(dict[str, object], case["promotion"])["requested_at"]:
        _fail("Character ADR-044 Receipt does not bind the reviewed requested_at")
    if request_status.record != final_status.record:
        _fail("Character known answer must reuse one exact complete status Record")
    return _KnownAnswerMaterials(
        upstream=upstream,
        request_status=request_status,
        final_status=final_status,
        primary_bible=bible,
        primary_asset_version=asset,
    )


def _scene_role(scene_source: dict[str, object], role_name: str) -> dict[str, object]:
    roles = scene_source.get("synthetic_role_records")
    if type(roles) is not list:
        _fail("Scene retained roles are missing")
    matches = [
        item
        for item in cast(list[object], roles)
        if type(item) is dict and cast(dict[str, object], item).get("role") == role_name
    ]
    if len(matches) != 1:
        _fail(f"Scene source must contain exactly one {role_name} role")
    return cast(dict[str, object], matches[0])


def _scene_upstream_closure(
    protected: _ProtectedInputs,
    case: dict[str, object],
    scene_source: dict[str, object],
) -> rights_codegen._UpstreamClosure:
    source = _old_json(
        protected,
        _CANDIDATE_SOURCE_PATH,
        label="frozen ADR-043 reviewed source fixture",
    )
    generated = _old_json(
        protected,
        _CANDIDATE_GENERATED_PATH,
        label="frozen ADR-043 generated fixture",
    )
    case_id = cast(str, cast(dict[str, object], case["upstream"])["candidate_case_id"])
    source_case = _document_case(source, case_id=case_id, label="ADR-043 reviewed source")
    generated_case = _document_case(generated, case_id=case_id, label="ADR-043 generated fixture")
    artifact = cast(
        CreativeSampleReferenceVisualPromptArtifactV1,
        _model_from_value(
            generated_case.get("artifact"),
            CreativeSampleReferenceVisualPromptArtifactV1,
            label="Scene ADR-042 Artifact",
        ),
    )
    outcome = cast(
        candidate_module.CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
        _model_from_value(
            generated_case.get("provider_attempt_outcome"),
            candidate_module.CreativeSampleGeneratedReferenceProviderAttemptOutcomeV1,
            label="Scene ADR-043 Provider Attempt Outcome",
        ),
    )
    candidate = cast(
        candidate_module.CreativeSampleGeneratedReferenceCandidateV1,
        _model_from_value(
            generated_case.get("candidate"),
            candidate_module.CreativeSampleGeneratedReferenceCandidateV1,
            label="Scene ADR-043 Candidate",
        ),
    )
    qualification_request = cast(
        candidate_module.CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
        _model_from_value(
            generated_case.get("qualification_request"),
            candidate_module.CreativeSampleGeneratedReferenceCandidateQualificationRequestV1,
            label="Scene ADR-043 Qualification Request",
        ),
    )
    qualification_decision = cast(
        candidate_module.CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
        _model_from_value(
            generated_case.get("qualification_decision"),
            candidate_module.CreativeSampleGeneratedReferenceCandidateQualificationDecisionV1,
            label="Scene ADR-043 Qualification Decision",
        ),
    )
    evidence_inputs = candidate_codegen._build_evidence_inputs(
        source_case.get("evidence_documents")
    )
    qualifier_role = _scene_role(scene_source, "QUALIFICATION_QUALIFIER")
    qualifier_identity = _canonical_document_bytes(source_case.get("qualifier_reference"))
    if _canonical_document_bytes(qualifier_role.get("identity_record")) != qualifier_identity:
        _fail("Scene source Qualification Qualifier identity differs from exact ADR-043 bytes")
    return rights_codegen._UpstreamClosure(
        artifact=artifact,
        outcome=outcome,
        candidate=candidate,
        qualification_request=qualification_request,
        qualification_decision=qualification_decision,
        evidence_inputs=evidence_inputs,
        preparer_identity_bytes=_canonical_document_bytes(source_case.get("preparer_reference")),
        preparer_action_bytes=_canonical_document_bytes(source_case.get("preparer_action")),
        qualifier_identity_bytes=qualifier_identity,
        qualifier_action_bytes=_canonical_document_bytes(source_case.get("qualifier_action")),
        png_bytes=protected.raw(_SCENE_PNG_PATH),
    )


def _canonical_status_refs(
    inputs: Sequence[rights_module.GeneratedReferenceCurrentStatusObservationInput],
) -> tuple[rights_module.GeneratedReferenceCurrentStatusObservationRefV1, ...]:
    observations = tuple(item.observation for item in inputs)
    return rights_codegen._canonical_request_refs(observations)


def _status_category_results(
    *,
    request: rights_module.CreativeSampleGeneratedReferenceCurrentStatusRequestV1,
    inputs: Sequence[rights_module.GeneratedReferenceCurrentStatusObservationInput],
    evaluated_at: str,
) -> tuple[rights_module.GeneratedReferenceCurrentStatusCategoryResultV1, ...]:
    observation_by_id = {item.observation.observation_id: item.observation for item in inputs}
    results: list[rights_module.GeneratedReferenceCurrentStatusCategoryResultV1] = []
    for ordinal, category in enumerate(rights_module.CURRENT_STATUS_CATEGORY_ORDER):
        refs = tuple(item for item in request.observation_refs if item.category == category)
        relied = tuple(
            item
            for item in refs
            if observation_by_id[item.observation_id].claim_value != "NOT_ASSESSED"
            and max(observation_by_id[item.observation_id].observed_at, item.valid_from)
            <= evaluated_at
            < item.valid_until
        )
        claims = {observation_by_id[item.observation_id].claim_value for item in relied}
        if not relied or len(claims) != 1:
            _fail("Scene positive current-status known answer is missing or conflicting")
        claim = next(iter(claims))
        if ordinal < 4:
            if claim != "ABSENT_WITH_EVIDENCE":
                _fail("Scene positive status lacks explicit adverse-absence evidence")
            effect: Literal["ADVERSE_ABSENT", "POSITIVE_PRESENT"] = "ADVERSE_ABSENT"
        else:
            if claim != "PRESENT":
                _fail("Scene positive status lacks one required positive predicate")
            effect = "POSITIVE_PRESENT"
        results.append(
            rights_module.GeneratedReferenceCurrentStatusCategoryResultV1(
                ordinal=ordinal,
                category=category,
                claim_value=claim,
                deterministic_effect=effect,
                category_observation_refs=refs,
                relied_on_observation_refs=relied,
                result_valid_until=min(
                    request.request_valid_until,
                    request.subject_closure.manifest_valid_until,
                    *(item.valid_until for item in relied),
                ),
            )
        )
    return tuple(results)


def _scene_status_closure(
    *,
    manifest: rights_module.CreativeSampleGeneratedReferenceRightsManifestV1,
    scene_source: dict[str, object],
    status_source: dict[str, object],
) -> promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput:
    subject = rights_module.build_generated_reference_current_status_subject_closure(manifest)
    raw_observations = cast(list[object], status_source["observations"])
    built_by_key: dict[str, rights_module.GeneratedReferenceCurrentStatusObservationInput] = {}
    raw_by_key: dict[str, dict[str, object]] = {}
    ordered_inputs: list[rights_module.GeneratedReferenceCurrentStatusObservationInput] = []
    for raw in raw_observations:
        source = cast(dict[str, object], raw)
        key = cast(str, source["observation_key"])
        predecessor_keys = cast(list[object], source["predecessor_observation_keys"])
        if any(cast(str, item) not in built_by_key for item in predecessor_keys):
            _fail("Scene status observations are not in complete topological order")
        predecessor_heads = tuple(
            rights_module.generated_reference_current_status_chain_head(
                built_by_key[cast(str, item)].observation
            )
            for item in predecessor_keys
        )
        canonical_heads = tuple(
            sorted(
                predecessor_heads,
                key=lambda item: (
                    item.observation_id,
                    item.observation_sha256,
                    item.chain_sha256,
                ),
            )
        )
        if predecessor_heads != canonical_heads:
            _fail("Scene reconciliation predecessor order is not canonical")
        observation = rights_module.build_generated_reference_current_status_source_observation(
            subject_closure=subject,
            category=cast(rights_module.CurrentStatusCategory, source["category"]),
            claim_value=cast(rights_module.CurrentStatusClaimValue, source["claim_value"]),
            source_kind=cast(rights_module.CurrentStatusSourceKind, source["source_kind"]),
            basis_code=cast(rights_module.CurrentStatusBasisCode, source["basis_code"]),
            basis_note=cast(str, source["basis_note"]),
            source_identity_bytes=_canonical_document_bytes(source["source_reference"]),
            source_object_ref=cast(str, source["source_object_ref"]),
            source_object_bytes=_canonical_document_bytes(source["source_object"]),
            source_object_media_type=cast(str, source["source_object_media_type"]),
            source_event_at=cast(str, source["source_event_at"]),
            observed_at=cast(str, source["observed_at"]),
            valid_from=cast(str, source["valid_from"]),
            valid_until=cast(str, source["valid_until"]),
            link_kind=cast(rights_module.CurrentStatusLinkKind, source["link_kind"]),
            predecessor_heads=predecessor_heads,
        )
        item = rights_module.GeneratedReferenceCurrentStatusObservationInput(
            observation=observation,
            document_bytes=rights_module.generated_reference_contract_document_bytes(observation),
        )
        built_by_key[key] = item
        raw_by_key[key] = source
        ordered_inputs.append(item)

    target_inputs = tuple(
        built_by_key[cast(str, source["observation_key"])]
        for source in raw_by_key.values()
        if source["target"] is True
    )
    expected_refs = _canonical_status_refs(target_inputs)
    preparer_role = _scene_role(scene_source, cast(str, status_source["preparer_role"]))
    checker_role = _scene_role(scene_source, cast(str, status_source["checker_role"]))
    preparer_identity = _canonical_document_bytes(preparer_role["identity_record"])
    checker_identity = _canonical_document_bytes(checker_role["identity_record"])
    preparer_semantics = cast(dict[str, object], preparer_role["action_semantics"])
    checker_semantics = cast(dict[str, object], checker_role["action_semantics"])
    requested_at = cast(str, status_source["requested_at"])
    evaluated_at = cast(str, status_source["evaluated_at"])
    if (
        preparer_semantics.get("action")
        != "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST"
        or preparer_semantics.get("requested_at") != requested_at
        or checker_semantics.get("action")
        != "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION"
        or checker_semantics.get("evaluated_at") != evaluated_at
    ):
        _fail("Scene status retained action semantics or times drifted")
    request_valid_until = _format_utc(
        min(
            _parse_utc(requested_at, field="Scene status requested_at")
            + timedelta(seconds=86_400),
            _parse_utc(manifest.manifest_valid_until, field="Scene manifest_valid_until"),
        )
    )
    if request_valid_until != status_source["expected_request_valid_until"]:
        _fail("Scene status Request deadline differs from the reviewed known answer")
    request_basis = cast(str, status_source["request_basis"])
    preparer_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_CURRENT_STATUS_REQUEST",
            "actor_identity_ref_sha256": _raw_sha256(preparer_identity),
            "subject_closure_sha256": subject.closure_sha256,
            "policy_document_sha256": (
                rights_module.GENERATED_REFERENCE_CURRENT_STATUS_POLICY_DOCUMENT_SHA256
            ),
            "requested_at": requested_at,
            "request_valid_until": request_valid_until,
            "observation_target_refs": [_explicit(item) for item in expected_refs],
            "request_basis": request_basis,
        }
    )
    request = rights_module.build_generated_reference_current_status_request(
        subject_closure=subject,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        requested_at=requested_at,
        target_observations=target_inputs,
        request_basis=request_basis,
    )
    if request.observation_refs != expected_refs:
        _fail("Scene status Request target refs differ from independent canonicalization")
    ref_by_id = {item.observation_id: item for item in request.observation_refs}

    def ancestor_keys(key: str, visiting: tuple[str, ...] = ()) -> set[str]:
        if key in visiting:
            _fail("Scene status source contains a cycle")
        source = raw_by_key[key]
        result = {key}
        for predecessor in cast(list[object], source["predecessor_observation_keys"]):
            result.update(ancestor_keys(cast(str, predecessor), (*visiting, key)))
        return result

    chains: list[rights_module.GeneratedReferenceCurrentStatusExplicitChainInput] = []
    for target in target_inputs:
        key = next(
            source_key
            for source_key, item in built_by_key.items()
            if item.observation.observation_id == target.observation.observation_id
        )
        members = ancestor_keys(key)
        chains.append(
            rights_module.GeneratedReferenceCurrentStatusExplicitChainInput(
                target_observation_refs=(ref_by_id[target.observation.observation_id],),
                observation_inputs=tuple(
                    item
                    for source_key, item in built_by_key.items()
                    if source_key in members
                ),
            )
        )
    chain_inputs = tuple(
        sorted(
            chains,
            key=lambda item: (
                item.observation_inputs[0].observation.chain_link.chain_scope_sha256,
                item.observation_inputs[0].observation.observation_id,
            ),
        )
    )
    category_results = _status_category_results(
        request=request,
        inputs=ordered_inputs,
        evaluated_at=evaluated_at,
    )
    status_valid_until = min(item.result_valid_until for item in category_results)
    if status_valid_until != status_source["expected_status_valid_until"]:
        _fail("Scene current-status deadline differs from the reviewed known answer")
    checker_basis = cast(str, status_source["checker_basis"])
    checker_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-current-status-decision-checker-action.v1"
            ),
            "action": "RECORDED_GENERATED_REFERENCE_CURRENT_STATUS_DECISION",
            "actor_identity_ref_sha256": _raw_sha256(checker_identity),
            "request_sha256": request.request_sha256,
            "evaluated_at": evaluated_at,
            "category_results": [_explicit(item) for item in category_results],
            "checker_basis": checker_basis,
            "status_valid_until": status_valid_until,
            "recorded_status": "CURRENT",
        }
    )
    instruction = rights_module.build_generated_reference_current_status_instruction(
        request=request,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
        evaluated_at=evaluated_at,
        checker_basis=checker_basis,
    )
    if instruction.category_results != category_results:
        _fail("Scene current-status category results differ from independent calculation")
    decision = rights_module.build_generated_reference_current_status_decision(
        request=request,
        instruction=instruction,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    record = rights_module.build_generated_reference_current_status_evidence_record(
        request=request,
        instruction=instruction,
        decision=decision,
        chain_inputs=chain_inputs,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )
    process = _process_status_record_as_of(
        record,
        manifest,
        chain_inputs,
        as_of=cast(str, status_source["as_of"]),
    )
    rights_module.verify_generated_reference_current_status_record_as_of_assessment_receipt(
        process.receipt,
        record=record,
        manifest=manifest,
        chain_inputs=chain_inputs,
    )
    if (
        decision.recorded_status != status_source["expected_recorded_status"]
        or process.assessment.as_of_status != status_source["expected_as_of_status"]
    ):
        _fail("Scene current-status replay differs from the reviewed known answer")
    return promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput(
        subject_closure=subject,
        request=request,
        instruction=instruction,
        decision=decision,
        record=record,
        chain_inputs=chain_inputs,
        receipt=process.receipt,
        status_preparer_identity_bytes=preparer_identity,
        status_preparer_action_bytes=preparer_action,
        status_checker_identity_bytes=checker_identity,
        status_checker_action_bytes=checker_action,
    )


def _scene_materials(
    protected: _ProtectedInputs, case: dict[str, object]
) -> _KnownAnswerMaterials:
    scene_source = cast(dict[str, object], case["scene_rights_current_status"])
    upstream_closure = _scene_upstream_closure(protected, case, scene_source)
    manifest_case = {
        "manifest": scene_source["manifest"],
        "synthetic_role_records": scene_source["synthetic_role_records"],
    }
    manifest_closure = rights_codegen._build_manifest(manifest_case, upstream_closure)
    manifest_source = cast(dict[str, object], scene_source["manifest"])
    upstream = _upstream_input(
        upstream_closure=upstream_closure,
        manifest_closure=manifest_closure,
        manifest_source=manifest_source,
    )
    request_status = _scene_status_closure(
        manifest=manifest_closure.manifest,
        scene_source=scene_source,
        status_source=cast(dict[str, object], scene_source["request_status"]),
    )
    final_status = _scene_status_closure(
        manifest=manifest_closure.manifest,
        scene_source=scene_source,
        status_source=cast(dict[str, object], scene_source["promotion_status"]),
    )
    prior_ordinals = {
        (item.observation_id, item.observation_sha256, item.chain_sha256): item.ordinal
        for item in request_status.request.observation_refs
    }
    final_ordinals = {
        (item.observation_id, item.observation_sha256, item.chain_sha256): item.ordinal
        for item in final_status.request.observation_refs
    }
    retained_final_targets = prior_ordinals.keys() & final_ordinals.keys()
    if not retained_final_targets or not any(
        prior_ordinals[item] != final_ordinals[item] for item in retained_final_targets
    ):
        _fail("Scene final target ordinals were not independently recanonicalized")
    bible, asset = _primary_asset_closure(protected, case)
    _assert_upstream_anchors(case, upstream)
    return _KnownAnswerMaterials(
        upstream=upstream,
        request_status=request_status,
        final_status=final_status,
        primary_bible=bible,
        primary_asset_version=asset,
    )


_COMPILER_PROMOTION_GATE_BASES = (
    "COMPILER_REVALIDATED_EXACT_CANDIDATE_OCCURRENCE_AND_RAW_MEDIA",
    "COMPILER_REVALIDATED_EXACT_SUCCESSFUL_OUTCOME_AND_ARTIFACT",
    "COMPILER_REVALIDATED_POSITIVE_UNEXPIRED_QUALIFICATION",
    "COMPILER_REVALIDATED_VALID_GENERATED_RIGHTS_MANIFEST",
    "COMPILER_REPLAYED_GENERATED_CURRENT_STATUS_AT_PROMOTION",
    "COMPILER_REVALIDATED_FINAL_SUPPLIED_PRIMARY_ASSET_BINDING",
    "COMPILER_REVALIDATED_EXACT_MANIFEST_REVIEWED_RIGHTS_SCOPE",
    None,
    None,
    "COMPILER_REVALIDATED_PROMOTION_ROLE_SEPARATION",
)


def _request_review_payload(
    *,
    materials: _KnownAnswerMaterials,
    binding: promotion_module.GeneratedReferencePromotionPrimaryAssetBindingV1,
    requested_at: str,
    request_basis: str,
) -> tuple[dict[str, object], str]:
    upstream = materials.upstream
    receipt = materials.request_status.receipt
    request_valid_until = _format_utc(
        min(
            _parse_utc(requested_at, field="Promotion requested_at")
            + timedelta(seconds=86_400),
            _parse_utc(
                upstream.qualification_decision.qualification_valid_until,
                field="Qualification valid_until",
            ),
            _parse_utc(upstream.manifest.manifest_valid_until, field="Manifest valid_until"),
            _parse_utc(receipt.status_valid_until, field="request status valid_until"),
        )
    )
    projection: dict[str, object] = {
        "policy_id": "sdc.generated-reference-asset-promotion-policy",
        "policy_version": "1.0.0",
        "policy_document_sha256": (
            "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
        ),
        "request_scope": "GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_ONLY",
        "reference_prompt_artifact_sha256": upstream.artifact.artifact_sha256,
        "provider_attempt_outcome_id": upstream.outcome.outcome_id,
        "provider_attempt_outcome_sha256": upstream.outcome.outcome_sha256,
        "candidate_id": upstream.candidate.candidate_id,
        "candidate_sha256": upstream.candidate.candidate_sha256,
        "output_ordinal": 0,
        "media_type": "image/png",
        "media_content_sha256": upstream.candidate.media_content_sha256,
        "media_size_bytes": upstream.candidate.media_size_bytes,
        "media_technical_record_sha256": upstream.candidate.media_technical_record_sha256,
        "qualification_request_id": upstream.qualification_request.request_id,
        "qualification_request_sha256": upstream.qualification_request.request_sha256,
        "qualification_decision_id": upstream.qualification_decision.decision_id,
        "qualification_decision_sha256": upstream.qualification_decision.decision_sha256,
        "qualification_decision_at": upstream.qualification_decision.decision_at,
        "qualification_valid_until": upstream.qualification_decision.qualification_valid_until,
        "manifest_id": upstream.manifest.manifest_id,
        "manifest_sha256": upstream.manifest.manifest_sha256,
        "manifest_at": upstream.manifest.manifest_at,
        "manifest_valid_until": upstream.manifest.manifest_valid_until,
        "reviewed_rights_scope": _rights_scope_projection(
            upstream.manifest.reviewed_rights_scope
        ),
        "status_subject_closure_id": materials.request_status.subject_closure.closure_id,
        "status_subject_closure_sha256": materials.request_status.subject_closure.closure_sha256,
        "requested_status_record_id": materials.request_status.record.record_id,
        "requested_status_record_sha256": materials.request_status.record.record_sha256,
        "requested_status_receipt_id": receipt.receipt_id,
        "requested_status_receipt_sha256": receipt.receipt_sha256,
        "requested_explicit_chain_set_sha256": receipt.explicit_chain_set_sha256,
        "requested_coverage_set_sha256": receipt.coverage_set_sha256,
        "requested_joint_replay_sha256": receipt.joint_replay_sha256,
        "requested_as_of_assessment_sha256": receipt.as_of_assessment_sha256,
        "requested_as_of": requested_at,
        "requested_as_of_status": "CURRENT",
        "requested_status_valid_until": receipt.status_valid_until,
        "requested_primary_asset_binding": _primary_binding_projection(
            binding, include_digest=True
        ),
        "requested_at": requested_at,
        "request_valid_until": request_valid_until,
        "request_basis": request_basis,
        "requested_representation": "TYPED_ELIGIBLE_ASSET_SIDECAR",
        "composite_media_unsplit": True,
        "role_assignment_embedded": False,
        "bible_mutation_requested": False,
        "provider_input_requested": False,
    }
    if tuple(projection) != _REVIEW_PAYLOAD_FIELDS:
        _fail("independent Promotion review-payload fields drifted")
    return projection, _semantic_sha256(_REVIEW_PAYLOAD_DOMAIN, projection)


def _promotion_gate_results(
    promotion_source: dict[str, object],
) -> tuple[promotion_module.GeneratedReferencePromotionGateResultV1, ...]:
    raw_human = cast(list[object], promotion_source["human_gate_results"])
    human_by_gate = {
        cast(str, cast(dict[str, object], item)["gate"]): cast(dict[str, object], item)
        for item in raw_human
    }
    gates: list[promotion_module.GeneratedReferencePromotionGateResultV1] = []
    for ordinal, gate in enumerate(promotion_module.PROMOTION_GATE_ORDER):
        if ordinal in {7, 8}:
            source = human_by_gate[gate]
            result = cast(str, source["result"])
            basis = cast(str, source["basis"])
        else:
            result = "PASS"
            basis = cast(str, _COMPILER_PROMOTION_GATE_BASES[ordinal])
        gates.append(
            promotion_module.GeneratedReferencePromotionGateResultV1.model_validate(
                {
                    "ordinal": ordinal,
                    "gate": gate,
                    "result": result,
                    "basis": basis,
                }
            )
        )
    return tuple(gates)


def _status_topology(
    closure: promotion_module.GeneratedReferenceAssetPromotionStatusClosureInput,
) -> dict[str, object]:
    occurrences: dict[tuple[str, str, str], object] = {}
    chains: list[dict[str, object]] = []
    for chain in closure.chain_inputs:
        chain_occurrences: list[dict[str, object]] = []
        for item in chain.observation_inputs:
            observation = item.observation
            anchor = (
                observation.observation_id,
                observation.observation_sha256,
                rights_module.generated_reference_current_status_chain_sha256(observation),
            )
            occurrences[anchor] = observation
            chain_occurrences.append(
                {
                    "observation_id": anchor[0],
                    "observation_sha256": anchor[1],
                    "chain_sha256": anchor[2],
                }
            )
        chains.append(
            {
                "target_observation_refs": [
                    _explicit(item) for item in chain.target_observation_refs
                ],
                "observation_occurrence_anchors": chain_occurrences,
            }
        )
    ordered_occurrences = [
        {
            "anchor": {
                "observation_id": anchor[0],
                "observation_sha256": anchor[1],
                "chain_sha256": anchor[2],
            },
            "observation": _explicit(occurrences[anchor]),
        }
        for anchor in sorted(occurrences)
    ]
    return {
        "explicit_chains": chains,
        "observation_occurrences": ordered_occurrences,
        "target_observation_refs": [_explicit(item) for item in closure.request.observation_refs],
    }


def _promotion_known_answer_case(
    protected: _ProtectedInputs,
    case: dict[str, object],
) -> dict[str, object]:
    materials = (
        _character_materials(protected, case)
        if case["case_id"] == _CASE_IDS[0]
        else _scene_materials(protected, case)
    )
    promotion_source = cast(dict[str, object], case["promotion"])
    requested_at = cast(str, promotion_source["requested_at"])
    promotion_at = cast(str, promotion_source["promotion_at"])
    request_basis = cast(str, promotion_source["request_basis"])
    promotion_basis = cast(str, promotion_source["promotion_basis"])
    maker_identity = _canonical_document_bytes(promotion_source["maker_identity_record"])
    checker_identity = _canonical_document_bytes(promotion_source["checker_identity_record"])
    binding = promotion_module.build_generated_reference_promotion_primary_asset_binding(
        materials.primary_bible,
        materials.primary_asset_version,
    )
    review_projection, review_sha = _request_review_payload(
        materials=materials,
        binding=binding,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    maker_action = _canonical_document_bytes(
        {
            "document_profile": (
                "sdc.generated-reference-asset-promotion-request-preparation-action.v1"
            ),
            "action": "PREPARED_GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST",
            "actor_ref_sha256": _raw_sha256(maker_identity),
            "promotion_review_payload_sha256": review_sha,
            "candidate_sha256": materials.upstream.candidate.candidate_sha256,
            "manifest_sha256": materials.upstream.manifest.manifest_sha256,
            "requested_status_receipt_sha256": materials.request_status.receipt.receipt_sha256,
            "requested_primary_asset_binding_sha256": binding.primary_asset_binding_sha256,
            "policy_document_sha256": (
                "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
            ),
            "requested_at": requested_at,
        }
    )
    request = promotion_module.prepare_generated_reference_asset_promotion_request(
        materials.upstream,
        materials.request_status,
        materials.primary_bible,
        materials.primary_asset_version,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        requested_at=requested_at,
        request_basis=request_basis,
    )
    if _independent_review_payload_projection(request) != review_projection:
        _fail("production Request review payload differs from independent pre-action calculation")

    gates = _promotion_gate_results(promotion_source)
    if materials.final_status.receipt.as_of_status != "CURRENT":
        _fail("positive Promotion known answer final status must be CURRENT")
    checker_action = _canonical_document_bytes(
        {
            "document_profile": "sdc.generated-reference-asset-promotion-decision-action.v1",
            "action": "RECORDED_GENERATED_REFERENCE_ASSET_PROMOTION_DECISION",
            "actor_ref_sha256": _raw_sha256(checker_identity),
            "request_sha256": request.request_sha256,
            "policy_document_sha256": (
                "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
            ),
            "promotion_status_receipt_sha256": materials.final_status.receipt.receipt_sha256,
            "promotion_primary_asset_binding_sha256": binding.primary_asset_binding_sha256,
            "promotion_at": promotion_at,
            "gate_results": [_gate_projection(item) for item in gates],
            "promotion_issue_codes": [],
            "promotion_basis": promotion_basis,
            "decision": "APPROVE_ELIGIBLE_ASSET_SIDECAR",
            "sidecar_materialization_allowed": True,
        }
    )
    human_by_gate = {
        cast(str, cast(dict[str, object], item)["gate"]): cast(dict[str, object], item)
        for item in cast(list[object], promotion_source["human_gate_results"])
    }
    result = promotion_module.finalize_generated_reference_asset_promotion(
        request,
        materials.upstream,
        materials.request_status,
        materials.primary_bible,
        materials.primary_asset_version,
        materials.final_status,
        materials.primary_bible,
        materials.primary_asset_version,
        maker_identity_bytes=maker_identity,
        maker_action_bytes=maker_action,
        checker_identity_bytes=checker_identity,
        checker_action_bytes=checker_action,
        promotion_at=promotion_at,
        primary_sidecar_association_result="PASS",
        primary_sidecar_association_basis=cast(
            str,
            human_by_gate["HUMAN_PRIMARY_SIDECAR_ASSOCIATION_APPROVED"]["basis"],
        ),
        composite_unsplit_role_deferral_result="PASS",
        composite_unsplit_role_deferral_basis=cast(
            str,
            human_by_gate[
                "HUMAN_COMPOSITE_UNSPLIT_ROLE_DEFERRAL_ACKNOWLEDGED"
            ]["basis"],
        ),
        promotion_basis=promotion_basis,
    )
    if result.sidecar is None:
        _fail("positive Promotion finalization did not atomically return its Sidecar")
    decision = result.decision
    sidecar = result.sidecar
    identities = _assert_independent_identities(
        asset_version=materials.primary_asset_version,
        binding=binding,
        request=request,
        decision=decision,
        sidecar=sidecar,
    )
    production_checks = (
        promotion_module.generated_reference_primary_asset_version_projection(
            materials.primary_asset_version
        )
        == identities["legacy_primary_asset_version_projection"],
        promotion_module.generated_reference_primary_asset_version_projection_sha256(
            materials.primary_asset_version
        )
        == identities["legacy_primary_asset_version_projection_sha256"],
        promotion_module.generated_reference_promotion_primary_asset_binding_projection(binding)
        == identities["primary_asset_binding_projection"],
        promotion_module.generated_reference_promotion_primary_asset_binding_sha256(binding)
        == identities["primary_asset_binding_sha256"],
        promotion_module.generated_reference_asset_promotion_review_payload_projection(request)
        == identities["promotion_review_payload_projection"],
        promotion_module.generated_reference_asset_promotion_review_payload_sha256(request)
        == identities["promotion_review_payload_sha256"],
        promotion_module.creative_sample_generated_reference_asset_promotion_request_projection(
            request
        )
        == identities["request_projection"],
        promotion_module.creative_sample_generated_reference_asset_promotion_decision_projection(
            decision
        )
        == identities["decision_projection"],
        promotion_module.creative_sample_generated_reference_eligible_asset_sidecar_projection(
            sidecar
        )
        == identities["sidecar_projection"],
    )
    if not all(production_checks):
        _fail("production Promotion projection differs from independent known-answer calculation")
    return {
        "asset_purpose": request.requested_primary_asset_binding.asset_purpose,
        "case_id": case["case_id"],
        "decision": _explicit(decision),
        "decision_document_sha256": _raw_sha256(
            promotion_module.generated_reference_asset_promotion_contract_document_bytes(decision)
        ),
        **identities,
        "primary_asset_binding": _explicit(binding),
        "promotion_status_record": _explicit(materials.final_status.record),
        "promotion_status_receipt": _explicit(materials.final_status.receipt),
        "promotion_status_topology": _status_topology(materials.final_status),
        "request": _explicit(request),
        "request_document_sha256": _raw_sha256(
            promotion_module.generated_reference_asset_promotion_contract_document_bytes(request)
        ),
        "request_status_record": _explicit(materials.request_status.record),
        "request_status_receipt": _explicit(materials.request_status.receipt),
        "request_status_topology": _status_topology(materials.request_status),
        "sidecar": _explicit(sidecar),
        "sidecar_document_sha256": _raw_sha256(
            promotion_module.generated_reference_asset_promotion_contract_document_bytes(sidecar)
        ),
    }


def _assert_projection_field_sets() -> None:
    expected = (
        (
            promotion_module.CreativeSampleGeneratedReferenceAssetPromotionRequestV1,
            {"request_id", "request_sha256"},
            _REQUEST_PROJECTION_FIELDS,
        ),
        (
            promotion_module.CreativeSampleGeneratedReferenceAssetPromotionDecisionV1,
            {"decision_id", "decision_sha256"},
            _DECISION_PROJECTION_FIELDS,
        ),
        (
            promotion_module.CreativeSampleGeneratedReferenceEligibleAssetSidecarV1,
            {"sidecar_id", "sidecar_sha256"},
            _SIDECAR_PROJECTION_FIELDS,
        ),
    )
    for model_type, self_fields, projection_fields in expected:
        if (
            len(projection_fields) != len(set(projection_fields))
            or set(model_type.model_fields) - self_fields != set(projection_fields)
        ):
            _fail(f"independent {model_type.__name__} projection field set drifted")
    domains = (
        (
            _REVIEW_PAYLOAD_DOMAIN,
            promotion_module.GENERATED_REFERENCE_ASSET_PROMOTION_REVIEW_PAYLOAD_SHA256_DOMAIN,
        ),
        (
            _PRIMARY_ASSET_VERSION_DOMAIN,
            promotion_module.GENERATED_REFERENCE_PRIMARY_ASSET_VERSION_PROJECTION_SHA256_DOMAIN,
        ),
        (
            _PRIMARY_BINDING_DOMAIN,
            promotion_module.GENERATED_REFERENCE_PRIMARY_ASSET_BINDING_SHA256_DOMAIN,
        ),
        (
            _REQUEST_DOMAIN,
            promotion_module.GENERATED_REFERENCE_ASSET_PROMOTION_REQUEST_SHA256_DOMAIN,
        ),
        (
            _DECISION_DOMAIN,
            promotion_module.GENERATED_REFERENCE_ASSET_PROMOTION_DECISION_SHA256_DOMAIN,
        ),
        (
            _SIDECAR_DOMAIN,
            promotion_module.GENERATED_REFERENCE_ELIGIBLE_ASSET_SIDECAR_SHA256_DOMAIN,
        ),
    )
    if any(left != right for left, right in domains) or len({left for left, _ in domains}) != 6:
        _fail("six independent ADR-045 domains drifted or alias one another")


def _build_expected_closure(root: Path) -> _ExpectedClosure:
    _assert_projection_field_sets()
    protected = _load_protected_inputs(root)
    cases = _assert_source_shape(protected.reviewed_source)
    derived_cases = [_promotion_known_answer_case(protected, case) for case in cases]
    derived_value: dict[str, object] = {
        "cases": derived_cases,
        "known_answer_version": _KNOWN_ANSWER_VERSION,
        "promotion_policy_document_sha256": (
            "94375b15ceb47d216611adf8d32eb5bac5a5f7544268ff07eca3f59919a4f9f1"
        ),
        "reviewed_source": {
            "path": _REVIEWED_SOURCE_PATH,
            "raw_sha256": _raw_sha256(protected.reviewed_source_raw),
            "size_bytes": len(protected.reviewed_source_raw),
        },
        "upstream_inputs": [
            {
                "path": path,
                "raw_sha256": _raw_sha256(raw),
                "size_bytes": len(raw),
            }
            for path, raw in protected.old_fixture_raws
        ],
    }
    raw = _canonical_document_bytes(derived_value)
    if not 1 <= len(raw) <= _MAX_DERIVED_BYTES:
        _fail("derived known-answer fixture exceeds its fixed byte boundary")
    return _ExpectedClosure(
        protected=protected,
        derived_value=derived_value,
        derived_raw=raw,
    )


def _protected_file_infos(root: Path) -> tuple[os.stat_result, ...]:
    infos: list[os.stat_result] = []
    for relative_path in _PROTECTED_FINGERPRINTS:
        path = _safe_path(root, relative_path, label="protected input")
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise GeneratedReferenceAssetPromotionCodegenError(
                "protected input could not be inspected before update"
            ) from exc
        if not _is_regular_non_symlink(info) or info.st_nlink != 1:
            _fail("protected input must remain one regular non-symlink file with one link")
        infos.append(info)
    return tuple(infos)


def _write_exact_derived(root: Path, relative_path: str, raw: bytes) -> None:
    if relative_path != _DERIVED_FIXTURE_PATH:
        _fail("update attempted to write outside the single fixed derived-fixture allowlist")
    if type(raw) is not bytes or not 1 <= len(raw) <= _MAX_DERIVED_BYTES:
        _fail("derived fixture write bytes are outside the fixed boundary")
    _parse_canonical_document(raw, label="derived known-answer fixture write bytes")
    destination = _safe_path(root, relative_path, label="derived known-answer fixture")
    protected_infos = _protected_file_infos(root)
    descriptor: int | None = None
    raw_windows_handle: int | None = None
    windows_guards: list[int] = []
    posix_guards: list[int] = []
    opened: os.stat_result
    after_handle: os.stat_result
    after_path: os.stat_result
    actual = b""
    try:
        if sys.platform == "win32":
            guard_path = root
            windows_guards.append(_acquire_windows_directory_guard(guard_path))
            for part in Path(relative_path).parts[:-1]:
                guard_path /= part
                windows_guards.append(_acquire_windows_directory_guard(guard_path))
            try:
                before = os.lstat(destination)
            except FileNotFoundError:
                before = None
            if before is not None and (
                not _is_regular_non_symlink(before) or before.st_nlink != 1
            ):
                _fail("derived fixture destination must be one regular non-symlink file")
            kernel32 = _windows_ctypes.WinDLL("kernel32", use_last_error=True)
            create_file = kernel32.CreateFileW
            create_file.argtypes = (
                _windows_wintypes.LPCWSTR,
                _windows_wintypes.DWORD,
                _windows_wintypes.DWORD,
                _windows_wintypes.LPVOID,
                _windows_wintypes.DWORD,
                _windows_wintypes.DWORD,
                _windows_wintypes.HANDLE,
            )
            create_file.restype = _windows_wintypes.HANDLE
            handle = create_file(
                str(destination),
                0x80000000 | 0x40000000 | 0x00000080,
                0,
                None,
                1 if before is None else 3,
                0x00000080 | 0x00200000,
                None,
            )
            invalid = _windows_ctypes.c_void_p(-1).value
            if handle == invalid:
                error = _windows_ctypes.get_last_error()
                raise OSError(error, "CreateFileW anchored derived fixture open failed")
            raw_windows_handle = int(handle)
            windows_opened = _windows_handle_snapshot(raw_windows_handle)
            if (
                bool(windows_opened.attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
                or bool(windows_opened.attributes & 0x10)
                or windows_opened.link_count != 1
                or (
                    before is not None
                    and windows_opened.identity != (before.st_dev, before.st_ino)
                )
            ):
                _fail("Windows derived fixture handle is unsafe or changed before open")
            descriptor = _windows_msvcrt.open_osfhandle(
                raw_windows_handle,
                os.O_RDWR | int(getattr(os, "O_BINARY", 0)),
            )
            raw_windows_handle = None
            opened = os.fstat(descriptor)
            if windows_opened.identity != (opened.st_dev, opened.st_ino):
                _fail("Windows derived fixture handle identity changed during admission")
        else:
            no_follow = getattr(os, "O_NOFOLLOW", None)
            directory = getattr(os, "O_DIRECTORY", None)
            close_on_exec = getattr(os, "O_CLOEXEC", None)
            if (
                type(no_follow) is not int
                or type(directory) is not int
                or type(close_on_exec) is not int
                or os.open not in os.supports_dir_fd
                or os.stat not in os.supports_dir_fd
                or os.stat not in os.supports_follow_symlinks
            ):
                _fail("this host cannot enforce anchored no-follow fixture writes")
            directory_flags = os.O_RDONLY | directory | no_follow | close_on_exec
            root_before = os.lstat(root)
            root_descriptor = os.open(root, directory_flags)
            posix_guards.append(root_descriptor)
            root_opened = os.fstat(root_descriptor)
            if (
                not _is_directory_non_symlink(root_before)
                or not _is_directory_non_symlink(root_opened)
                or not _same_file(root_before, root_opened)
            ):
                _fail("repository root changed before anchored directory admission")
            parent_descriptor = root_descriptor
            for part in Path(relative_path).parts[:-1]:
                ancestor_before = os.stat(
                    part,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                ancestor_descriptor = os.open(
                    part,
                    directory_flags,
                    dir_fd=parent_descriptor,
                )
                posix_guards.append(ancestor_descriptor)
                ancestor_opened = os.fstat(ancestor_descriptor)
                if (
                    not _is_directory_non_symlink(ancestor_before)
                    or not _is_directory_non_symlink(ancestor_opened)
                    or not _same_file(ancestor_before, ancestor_opened)
                ):
                    _fail("derived fixture ancestor changed during anchored admission")
                parent_descriptor = ancestor_descriptor
            leaf_name = Path(relative_path).parts[-1]
            try:
                before = os.stat(
                    leaf_name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                before = None
            if before is not None and (
                not _is_regular_non_symlink(before) or before.st_nlink != 1
            ):
                _fail("derived fixture destination must be one regular non-symlink file")
            file_flags = os.O_RDWR | no_follow | close_on_exec
            if before is None:
                file_flags |= os.O_CREAT | os.O_EXCL
            descriptor = os.open(
                leaf_name,
                file_flags,
                0o644,
                dir_fd=parent_descriptor,
            )
            opened = os.fstat(descriptor)
        if not _is_regular_non_symlink(opened) or opened.st_nlink != 1:
            _fail("opened derived fixture is not one regular file")
        if before is not None and not _same_file(before, opened):
            _fail("derived fixture destination changed before it was opened")
        if any(_same_file(info, opened) for info in protected_infos):
            _fail("opened derived fixture aliases a protected input")
        os.ftruncate(descriptor, 0)
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                _fail("derived fixture write made no progress")
            offset += written
        os.fsync(descriptor)
        after_handle = os.fstat(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, len(raw) + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > len(raw):
                _fail("derived fixture handle contains unexpected trailing bytes")
        actual = b"".join(chunks)
        if sys.platform == "win32":
            windows_after = _windows_handle_snapshot(
                _windows_msvcrt.get_osfhandle(descriptor)
            )
            if (
                windows_after.identity != (after_handle.st_dev, after_handle.st_ino)
                or bool(windows_after.attributes & _WINDOWS_REPARSE_POINT_ATTRIBUTE)
                or bool(windows_after.attributes & 0x10)
                or windows_after.link_count != 1
                or windows_after.size_bytes != len(raw)
            ):
                _fail("Windows derived fixture handle changed while writing")
            after_path = os.lstat(destination)
        else:
            after_path = os.stat(
                Path(relative_path).parts[-1],
                dir_fd=posix_guards[-1],
                follow_symlinks=False,
            )
        if (
            not _is_regular_non_symlink(after_path)
            or after_path.st_nlink != 1
            or not _same_file(after_handle, after_path)
            or after_path.st_size != len(raw)
            or actual != raw
        ):
            _fail("derived fixture changed while it was written")
    except GeneratedReferenceAssetPromotionCodegenError:
        raise
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "derived fixture could not be written directly"
        ) from exc
    finally:
        if raw_windows_handle is not None:
            _close_windows_handle(raw_windows_handle)
        if descriptor is not None:
            os.close(descriptor)
        for handle in reversed(windows_guards):
            _close_windows_handle(handle)
        for handle in reversed(posix_guards):
            os.close(handle)
    try:
        final_path = os.lstat(destination)
    except OSError as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "derived fixture could not be re-inspected"
        ) from exc
    if (
        not _is_regular_non_symlink(final_path)
        or final_path.st_nlink != 1
        or not _same_file(after_handle, final_path)
        or final_path.st_size != len(raw)
    ):
        _fail("derived fixture path identity changed after its guarded write")
    if actual != raw:
        _fail("derived fixture final bytes differ from the requested bytes")


def _check_closure(root: Path, closure: _ExpectedClosure) -> None:
    path = _safe_path(root, _DERIVED_FIXTURE_PATH, label="derived known-answer fixture")
    actual = _read_stable_regular_file(
        path,
        max_bytes=_MAX_DERIVED_BYTES,
        label="derived known-answer fixture",
    )
    _parse_canonical_document(actual, label="derived known-answer fixture")
    if actual != closure.derived_raw:
        _fail("derived known-answer fixture is byte-stale")


def _update_closure(root: Path, closure: _ExpectedClosure) -> None:
    before = _load_protected_inputs(root)
    if before != closure.protected:
        _fail("a protected input changed before derived-fixture update")
    _write_exact_derived(root, _DERIVED_FIXTURE_PATH, closure.derived_raw)
    after = _load_protected_inputs(root)
    if after != closure.protected:
        _fail("a protected input changed during derived-fixture update")
    _check_closure(root, closure)


def _repository_root() -> Path:
    module_path = Path(__file__).resolve()
    root = module_path.parents[2]
    expected_parent = root / "src" / "sdc"
    if module_path.parent != expected_parent.resolve():
        _fail("codegen module is outside the frozen src/sdc repository layout")
    expected_core = expected_parent / "generated_reference_asset_promotion.py"
    if Path(promotion_module.__file__).resolve() != expected_core.resolve():
        _fail("Promotion core does not belong to the same fixed repository layout")
    pyproject = _safe_path(root, "pyproject.toml", label="repository pyproject.toml")
    raw = _read_stable_regular_file(
        pyproject,
        max_bytes=_MAX_REPOSITORY_METADATA_BYTES,
        label="repository pyproject.toml",
    )
    try:
        value = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GeneratedReferenceAssetPromotionCodegenError(
            "repository pyproject.toml is not strict UTF-8 TOML"
        ) from exc
    project = value.get("project")
    if type(project) is not dict or project.get("name") != "story-to-drama-compiler":
        _fail("repository pyproject.toml has the wrong project identity")
    return root


def _argument_parser() -> argparse.ArgumentParser:
    program = "python -B -m sdc.generated_reference_asset_promotion_codegen"
    parser = argparse.ArgumentParser(
        prog=program,
        description="Check or explicitly update the fixed ADR-045 known-answer fixture.",
        allow_abbrev=False,
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
    else:  # pragma: no cover
        _fail("one explicit codegen mode is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
